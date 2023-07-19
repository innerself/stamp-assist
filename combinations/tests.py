import django.test
import pytest

from accounts.models import User
from .models import StampSample, UserStamp


@pytest.mark.skip('Skip for now')
@pytest.mark.django_db
def test_sample_stamp_create():
    assert len(StampSample.objects.all()) == 0

    url = 'https://colnect.com/ru/stamps/stamp/' \
          '1186704-Ruslan_and_Lyudmila_by_Aleksander_Pushkin-' \
          'Europa_CEPT_2022_-_Stories_and_Myths-' \
          '%D0%A0%D0%BE%D1%81%D1%81%D0%B8%D1%8F'

    sample = StampSample.objects.from_colnect_url(url)

    assert sample.name == 'Ruslan and Lyudmila by Aleksander Pushkin'
    assert sample.year == 2022
    assert sample.country == 'Россия'
    assert sample.value == 55
    assert sample.michel_number == 'RU 3083'
    assert bool(sample.image) is True

    assert len(StampSample.objects.all()) == 1


class TestCombinations(django.test.TestCase):
    def test_single_stamp(self):
        user = User.objects.generate(target_value=10, max_value=10)
        sample = StampSample.objects.generate(value=10)
        UserStamp.objects.generate(user=user, sample=sample)

        combs = user.desk_available.combinations()

        assert len(combs) == 1

    def test_two_diff_stamps(self):
        user = User.objects.generate(target_value=10, max_value=10)

        for _ in range(2):
            sample = StampSample.objects.generate(value=10)
            UserStamp.objects.generate(user=user, sample=sample)

        combs = user.desk_available.combinations()

        assert len(combs) == 2

    def test_two_diff_stamps_half_value(self):
        user = User.objects.generate(target_value=10, max_value=10)

        for _ in range(2):
            sample = StampSample.objects.generate(value=5)
            UserStamp.objects.generate(user=user, sample=sample)

        combs = user.desk_available.combinations()

        assert len(combs) == 1

