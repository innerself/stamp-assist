import datetime
import itertools
import math
import random
import time
from dataclasses import dataclass
from decimal import Decimal
from functools import wraps
from logging import getLogger
from pathlib import Path
from typing import Self

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.text import slugify
from imagekitio import ImageKit
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions
from mimesis import Text, Locale, Datetime, Address, Finance, BinaryFile

from accounts.models import User
from stamp_assist.settings import env

imagekit = ImageKit(
    private_key=env('IMAGE_KIT_PRIVATE_KEY'),
    public_key=env('IMAGE_KIT_PUBLIC_KEY'),
    url_endpoint=env('IMAGE_KIT_ENDPOINT'),
)

logger = getLogger()

mim_text_en = Text(locale=Locale.EN)
mim_datetime = Datetime()
mim_address_en = Address(locale=Locale.EN)
mim_finance = Finance()
mim_binary_file = BinaryFile()


def cache_combinations(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        cache_key = f'combinations:{args[0].id}'  # Assuming args[0] is an instance of Desk
        cached_result = cache.get(cache_key)

        if cached_result is not None:
            return cached_result
        else:
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout=3600)  # Cache for 1 hour
            return result

    return wrapper


class DeskType(models.TextChoices):
    """
    AVAILABLE: stamps that user has
    POSTCARD: stamp that user put on the virtual postcard
    """
    AVAILABLE = 'available'
    POSTCARD = 'postcard'
    REMOVED = 'removed'


class DeskManager(models.QuerySet):
    pass


class Desk(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='desks', on_delete=models.CASCADE)
    type = models.CharField(max_length=100, choices=DeskType.choices)

    def __repr__(self):
        return f'{self.type.capitalize()} ({self.user.username})'

    @classmethod
    def desk_available(cls, user: User) -> Self:
        return cls.objects.get(user=user, type=DeskType.AVAILABLE)

    @classmethod
    def desk_postcard(cls, user: User) -> Self:
        return cls.objects.get(user=user, type=DeskType.POSTCARD)

    @classmethod
    def desk_removed(cls, user: User) -> Self:
        return cls.objects.get(user=user, type=DeskType.REMOVED)

    def clear_cache(self):
        cache_key = f'combinations:{self.id}'  # Assuming args[0] is an instance of Desk
        cache.delete(cache_key)

    @cache_combinations
    def combinations(self):
        start = time.perf_counter()

        if self.user.allow_stamp_repeat:
            all_stamps = list(
                UserStamp.objects
                .filter(user=self.user)
                .exclude(desk=self.desk_removed(self.user))
                .prefetch_related('sample')
            )
        else:
            all_stamps = []
            added_samples = []
            for stamp in UserStamp.objects \
                    .filter(user=self.user) \
                    .exclude(desk=self.desk_removed(self.user)) \
                    .prefetch_related('sample'):

                if stamp.allow_repeat:
                    all_stamps.append(stamp)
                elif stamp.sample not in added_samples:
                    all_stamps.append(stamp)
                    added_samples.append(stamp.sample)

        combs_to_test = []
        total_combs = 0

        for st_num in range(self.user.stamps_min, self.user.stamps_max + 1):
            total_combs += math.comb(len(all_stamps), st_num)
            combs_to_test.append(itertools.combinations(all_stamps, st_num))

        if total_combs > env('COMBINATION_LIMIT'):
            raise ValidationError(
                'You have requested to calculate too much combinations. '
                'Please, narrow the desired number of stamps.'
            )

        logger.info(f'User {self.user.username} requested to evaluate {total_combs} combinations')
        t0 = time.perf_counter()
        logger.info(f'Preparation time: {t0 - start}')

        filtered_by_value = (
            comb for comb in itertools.chain(*combs_to_test)
            if self.user.target_value <= sum(stamp.sample.value for stamp in comb) <= self.user.max_value
        )

        stamps_to_include = set(
            x.id for x in UserStamp.objects.filter(
                user=self.user, desk=self.desk_postcard(self.id)
            )
        )
        added_combs = set()
        result_combs = []
        for comb in filtered_by_value:
            if stamps_to_include and not set(x.id for x in comb).issuperset(stamps_to_include):
                continue

            comb_string = tuple(sorted(str(stamp) for stamp in comb))
            if comb_string not in added_combs:
                result_combs.append(Combination(comb))
                added_combs.add(comb_string)

        t1 = time.perf_counter()
        logger.info(f'Filtering time: {t1 - t0}')
        logger.info(f'Total time is: {t1 - start}')
        logger.info(f'Resulting in {len(result_combs)} combinations')
        logger.info('= ' * 20)

        return sorted(result_combs, key=lambda x: x.sum())


class StampSampleManager(models.QuerySet):
    def from_colnect_url(self, url: str):
        """Create an instance from colnect.com URL."""
        if self.filter(url=url).exists():
            logger.warning(f'Sample from URL: {url} already imported')
            return None

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/104.0.5112.79 Safari/537.36',
        }
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, 'html.parser')

        try:
            image_url = f"https:{soup.find('div', {'class': 'item_z_pic'}).img['src']}"
        except AttributeError:
            logger.debug(f'Error importing image: {url}')
            return None

        ik_options = UploadFileRequestOptions(folder=env('IMAGE_KIT_FOLDER'))
        ik_image = imagekit.upload_file(
            image_url,
            file_name=Path(image_url).name,
            options=ik_options,
        )

        name = soup.find('span', id='name').string
        value = Decimal(soup.find(
            'dt', string='Номинальная стоимость:'
        ).next_sibling.next_element.text.replace(',', '.'))

        if michel_tag := soup.find('strong', string='Михель'):
            michel_number = michel_tag.next_sibling.text.strip()
        else:
            michel_number = None

        return self.create(
            name=name,
            slug=slugify(f'{name}-{value}'),
            year=datetime.date.fromisoformat(soup.find('dt', string='Дата выпуска:').next_sibling.text.strip()).year,
            country=soup.find('dt', string='Страна:').next_sibling.text.strip(),
            value=value,
            michel_number=michel_number,
            image=ik_image.url,
            url=url,
        )

    def update_slugs(self):
        for card in self.all():
            card.slug = slugify(f'{card.name}-{card.value}')
            card.save()

    def generate(self, **kwargs):
        name = kwargs.get('name', mim_text_en.title())
        return self.create(
            name=name,
            slug=slugify(name),
            year=kwargs.get('year', mim_datetime.year()),
            country=kwargs.get('country', mim_address_en.country()),
            value=kwargs.get('value', mim_finance.price(1, 101)),
            width=kwargs.get('width', random.randint(50, 400)),
            height=kwargs.get('height', random.randint(50, 400)),
            topics=kwargs.get('topics', mim_text_en.words(3)),
            michel_number=kwargs.get('michel_number', f'{mim_address_en.country_code()} {random.randint(1000, 9999)}'),
            image=kwargs.get('image', mim_binary_file.image()),
        )


class StampSample(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    year = models.PositiveSmallIntegerField()
    country = models.CharField(max_length=255)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    width = models.PositiveSmallIntegerField(null=True)
    height = models.PositiveSmallIntegerField(null=True)
    topics = models.JSONField(default=list)
    michel_number = models.CharField(max_length=255, null=True, blank=True)
    image = models.URLField(null=True)
    url = models.URLField(null=True, max_length=500)

    objects = StampSampleManager().as_manager()

    def __str__(self):
        return f'{self.name} ({self.value}, {self.year})'


class UserStampManager(models.QuerySet):
    def generate(self, *, user: User, **kwargs):
        desk = Desk.objects.get(user=user, type=DeskType.AVAILABLE)
        return self.create(
            sample=kwargs.get('sample', StampSample.objects.generate()),
            custom_name=kwargs.get('custom_name'),
            comment=kwargs.get('comment'),
            user=user,
            desk=kwargs.get('desk', desk),
            allow_repeat=kwargs.get('allow_repeat', False),
        )

    def to_json(self) -> list[dict]:
        return [{
            'sample_slug': stamp.sample.slug,
            'custom_name': stamp.custom_name,
            'comment': stamp.comment,
            'username': stamp.user.username,
            'desk_type': stamp.desk.type,
            'allow_repeat': stamp.allow_repeat,
        } for stamp in self]

    def from_json(self, stamps_raw_data: list[dict]) -> list:
        created_stamps = []
        for stamp in stamps_raw_data:
            user = User.objects.get(username=stamp['username'])
            created_stamp = self.create(
                sample=StampSample.objects.get(slug=stamp['sample_slug']),
                custom_name=stamp['custom_name'],
                comment=stamp['comment'],
                user=user,
                desk=Desk.objects.get(user=user, type=stamp['desk_type']),
                allow_repeat=stamp['allow_repeat'],
            )
            created_stamps.append(created_stamp)

        return created_stamps


class UserStamp(models.Model):
    sample = models.ForeignKey(StampSample, on_delete=models.CASCADE)
    custom_name = models.CharField(max_length=255, null=True, blank=True)
    comment = models.CharField(max_length=255, null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='stamps', on_delete=models.CASCADE)
    desk = models.ForeignKey(Desk, related_name='stamps', on_delete=models.PROTECT, null=True)
    allow_repeat = models.BooleanField(default=False)

    objects = UserStampManager.as_manager()

    def __add__(self, other) -> Decimal:
        if isinstance(other, self.__class__):
            return self.sample.value + other.sample.value
        elif isinstance(other, int) or isinstance(other, Decimal):
            return self.sample.value + other

    def __radd__(self, other) -> Decimal:
        return self + other

    def __lt__(self, other):
        if isinstance(other, self.__class__):
            return self.sample.value < other.sample.value
        elif isinstance(other, int) or isinstance(other, Decimal):
            return self.sample.value < other

    def __str__(self):
        if self.sample.name:
            return f'{self.sample.name} ({self.sample.value})'
        else:
            return f'id={self.id} value={self.sample.value}'

    def to_available(self):
        UserStamp.objects.filter(
            user=self.user,
            sample=self.sample,
        ).update(desk=Desk.desk_available(self.user))

    def to_postcard(self):
        self.desk = Desk.desk_postcard(self.user.id)
        self.save()

    def to_removed(self):
        self.desk = Desk.desk_removed(self.user.id)
        self.save()


@receiver(post_save, sender=User)
def desk_create(sender, instance=None, created=False, **kwargs):
    if created:
        Desk.objects.create(user=instance, type=DeskType.AVAILABLE)
        Desk.objects.create(user=instance, type=DeskType.POSTCARD)
        Desk.objects.create(user=instance, type=DeskType.REMOVED)


@dataclass
class Combination:
    stamps: list[UserStamp]

    def __eq__(self, other) -> bool:
        if isinstance(other, self.__class__):
            self_names = sorted([x.sample.name for x in self.stamps])
            other_names = sorted([x.sample.name for x in other.stamps])
            return self_names == other_names

        return NotImplemented

    def sum(self) -> Decimal:
        return sum(self.stamps)
