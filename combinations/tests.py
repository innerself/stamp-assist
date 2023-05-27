import pytest
from .models import StampSample


@pytest.mark.django_db
def test_sample_stamp_create():
    assert len(StampSample.objects.all()) == 0

    url = 'https://colnect.com/ru/stamps/stamp/' \
          '1186704-Ruslan_and_Lyudmila_by_Aleksander_Pushkin-' \
          'Europa_CEPT_2022_-_Stories_and_Myths-' \
          '%D0%A0%D0%BE%D1%81%D1%81%D0%B8%D1%8F'

    sample = StampSample.objects.from_colnect(url)

    assert sample.name == 'Ruslan and Lyudmila by Aleksander Pushkin'
    assert sample.year == 2022
    assert sample.country == 'Россия'
    assert sample.value == 55
    assert sample.michel_number == 'RU 3083'
    assert bool(sample.image) is True

    assert len(StampSample.objects.all()) == 1
