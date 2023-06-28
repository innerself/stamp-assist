import datetime
import enum
import io
import itertools
from decimal import Decimal
from pathlib import Path
from accounts.models import User
import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.files.images import ImageFile
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from imagekitio import ImageKit
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions

from stamp_assist.settings import env

imagekit = ImageKit(
    private_key=env('IMAGE_KIT_PRIVATE_KEY'),
    public_key=env('IMAGE_KIT_PUBLIC_KEY'),
    url_endpoint=env('IMAGE_KIT_ENDPOINT'),
)


class DeskType(models.TextChoices):
    """
    AVAILABLE: stamps that user has
    POSTCARD: stamp that user put on the virtual postcard
    """
    AVAILABLE = 'available'
    POSTCARD = 'postcard'


class Desk(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='desks', on_delete=models.CASCADE)
    type = models.CharField(max_length=100, choices=DeskType.choices)


class StampCollection(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def all_stamps(self, exclude_values: list[int] = None):
        stamps = []
        for block in self.blocks.all():
            stamps.extend([block.stamp] * block.number)
        return stamps

    def combinations(self):
        comb_groups = []
        combs = []
        comb_strings = []
        if self.user.stamps_count == 0:
            for st_num in range(1, 6):
                comb_groups.append(set(itertools.combinations(self.all_stamps(), st_num)))
        else:
            comb_groups.append(itertools.combinations(self.all_stamps(), self.user.stamps_count))

        for comb_group in comb_groups:
            for comb in comb_group:
                value_applies = self.user.target_value <= (c_sum := sum(comb)) <= self.user.max_value
                if value_applies and (c_srt := sorted(comb)) not in combs:
                    combs.append(c_srt)
                    comb_str = "<br> + ".join([str(x) for x in comb])
                    comb_strings.append(f'{comb_str}<br> = {c_sum}')

        return comb_strings

    def __str__(self):
        return f'{self.user} stamps collection'


class StampSampleManager(models.Manager):
    def from_colnect(self, url: str):
        """Create an instance from colnect.com URL."""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/104.0.5112.79 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, 'html.parser')

        image_url = f"https:{soup.find('div', {'class': 'item_z_pic'}).img['src']}"
        ik_options = UploadFileRequestOptions(folder='/stamp-assist/')
        ik_image = imagekit.upload_file(
            image_url,
            file_name=Path(image_url).name,
            options=ik_options,
        )

        return self.create(
            name=soup.find('span', id='name').string,
            year=datetime.date.fromisoformat(soup.find('dt', string='Дата выпуска:').next_sibling.text.strip()).year,
            country=soup.find('dt', string='Страна:').next_sibling.text.strip(),
            value=int(soup.find('dt', string='Номинальная стоимость:').next_sibling.next_element.text),
            michel_number=soup.find('strong', string='Михель').next_sibling.text.strip(),
            image=ik_image.url,
        )


class StampSample(models.Model):
    name = models.CharField(max_length=255)
    year = models.PositiveSmallIntegerField()
    country = models.CharField(max_length=255)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    width = models.PositiveSmallIntegerField(null=True)
    height = models.PositiveSmallIntegerField(null=True)
    topics = models.JSONField(default=list)
    michel_number = models.CharField(max_length=255, null=True, blank=True)
    image = models.URLField(null=True)

    objects = StampSampleManager()

    def __str__(self):
        return f'{self.name} ({self.value}, {self.year})'


class Stamp(models.Model):
    desk = models.ForeignKey(Desk, on_delete=models.PROTECT, null=True)

    def __add__(self, other) -> Decimal:
        if isinstance(other, self.__class__):
            return self.value + other.value
        elif isinstance(other, int) or isinstance(other, Decimal):
            return self.value + other

    def __radd__(self, other):
        return self + other

    def __lt__(self, other):
        if isinstance(other, self.__class__):
            return self.value < other.value
        elif isinstance(other, int) or isinstance(other, Decimal):
            return self.value < other

    def __str__(self):
        if self.name:
            return f'{self.name} ({self.value})'
        else:
            return f'Stamp id={self.id} value={self.value}'


class UserStamp(models.Model):
    sample = models.ForeignKey(StampSample, on_delete=models.CASCADE)
    comment = models.CharField(max_length=255, null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    desk = models.ForeignKey(Desk, related_name='user_stamps', on_delete=models.PROTECT, null=True)

    def __add__(self, other) -> Decimal:
        if isinstance(other, self.__class__):
            return self.sample.value + other.sample.value
        elif isinstance(other, int) or isinstance(other, Decimal):
            return self.sample.value + other

    def __radd__(self, other):
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

    @staticmethod
    def combinations(user: User):
        comb_groups = []
        combs = []
        comb_strings = []

        all_stamps = []
        for stamp in UserStamp.objects.filter(user=user):
            all_stamps.extend([stamp] * stamp.quantity)

        if user.stamps_count == 0:
            for st_num in range(1, 6):
                comb_groups.append(set(itertools.combinations(all_stamps, st_num)))
        else:
            comb_groups.append(itertools.combinations(all_stamps, user.stamps_count))

        for comb_group in comb_groups:
            for comb in comb_group:
                value_applies = user.target_value <= (c_sum := sum(comb)) <= user.max_value
                if value_applies and (c_srt := sorted(comb)) not in combs:
                    combs.append(c_srt)
                    comb_str = "<br> + ".join([str(x) for x in comb])
                    comb_strings.append(f'{comb_str}<br> = {c_sum}')

        return comb_strings


@receiver(post_save, sender=User)
def desk_create(sender, instance=None, created=False, **kwargs):
    if created:
        Desk.objects.create(user=instance, type=DeskType.AVAILABLE)
        Desk.objects.create(user=instance, type=DeskType.POSTCARD)
