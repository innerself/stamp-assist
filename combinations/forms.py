from django import forms


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

