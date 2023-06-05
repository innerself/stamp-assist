from django import forms

from combinations.models import StampSample

STAMPS_COUNT_CHOICES = (
    (0, '1-5'),
    (1, '1'),
    (2, '2'),
    (3, '3'),
    (4, '4'),
    (5, '5'),
)


class CalcConfigForm(forms.Form):
    stamps_count = forms.ChoiceField(choices=STAMPS_COUNT_CHOICES)
    target_value = forms.DecimalField(max_digits=10, decimal_places=2)
    max_value = forms.DecimalField(max_digits=10, decimal_places=2)


class ColnectCreateForm(forms.Form):
    urls = forms.CharField(widget=forms.Textarea(
        attrs={
            'cols': '150',
            'rows': '5',
            'class': 'form-control colnect-input',
        }))


class UserStampCreateForm(forms.Form):
    sample = forms.ModelChoiceField(queryset=StampSample.objects.all())
    quantity = forms.ChoiceField(choices=[(x, x) for x in range(1, 51)])
    comment = forms.CharField(max_length=255, required=False)
