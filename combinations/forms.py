from django import forms

from combinations.models import StampSample, UserStamp

STAMPS_COUNT_CHOICES = (
    (1, 1),
    (2, 2),
    (3, 3),
    (4, 4),
    (5, 5),
)


class CalcConfigForm(forms.Form):
    stamps_min = forms.ChoiceField(choices=STAMPS_COUNT_CHOICES)
    stamps_max = forms.ChoiceField(choices=STAMPS_COUNT_CHOICES)
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
    custom_name = forms.CharField(max_length=255, required=False)
    comment = forms.CharField(max_length=255, required=False)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user is not None:
            user_sample_ids = list(set(x.sample.id for x in user.stamps.all()))
            self.fields['sample'].queryset = StampSample.objects \
                .all() \
                .exclude(id__in=user_sample_ids) \
                .order_by('name')


class UserStampEditForm(forms.Form):
    original_name = forms.CharField(max_length=255, disabled=True, required=False)
    custom_name = forms.CharField(max_length=255, required=False)
    comment = forms.CharField(max_length=255, required=False)
    quantity = forms.IntegerField(disabled=True, required=False)
    quantity_change = forms.IntegerField(initial=0)
    allow_repeat = forms.BooleanField(initial=False, required=False)


class UserStampAddForm(forms.Form):
    original_name = forms.CharField(max_length=255, disabled=True, required=False)
    custom_name = forms.CharField(max_length=255, required=False)
    comment = forms.CharField(max_length=255, required=False)
    quantity = forms.IntegerField(initial=1, max_value=99, required=True)
    allow_repeat = forms.BooleanField(initial=False, required=False)
