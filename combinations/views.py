from decimal import Decimal

from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.views.generic import CreateView, ListView

from accounts.models import User
from .forms import CalcConfigForm, ColnectCreateForm
from .models import StampCollection, StampSample


def root_view(request):
    curr_user = User.objects.get(username='tyrel')
    # stamp_collection = StampCollection.objects.get(user=curr_user)
    #
    if request.method == 'POST':
        if all(field in request.POST.keys() for field in CalcConfigForm.declared_fields):
            new_settings = {
                'stamps_count': int(request.POST['stamps_count']),
                'target_value': Decimal(request.POST['target_value']),
                'max_value': Decimal(request.POST['max_value']),
            }

            curr_user.calc_settings = new_settings
            curr_user.save()
        # if block_id := request.POST.get('use-block'):
        #     block = StampBlock.objects.get(id=block_id)

    # combs = stamp_collection.combinations()

    curr_user.refresh_from_db()
    form = CalcConfigForm(initial=curr_user.calc_settings)

    context = {
        'form': form,
        # 'stamp_collection': stamp_collection,
        # 'combs': combs,
    }
    return render(request, 'combinations/index.html', context)


class StampSampleCreateView(CreateView):
    model = StampSample
    fields = '__all__'
    template_name = 'combinations/stamp-sample-create.html'


class StampSampleListView(ListView):
    model = StampSample
    template_name = 'combinations/stamp-sample-list.html'


@require_http_methods(['GET', 'POST'])
def samples_create_from_colnect_view(request):
    if request.method == 'POST':
        form = ColnectCreateForm(request.POST)
        if form.is_valid():
            urls = []
            if url := form.cleaned_data['url']:
                urls.append(url)
            else:
                urls.extend(form.cleaned_data['urls'].split('\n'))
            for url in urls:
                StampSample.objects.from_colnect(url)
    else:
        form = ColnectCreateForm()

    context = {'form': form}
    return render(request, 'combinations/stamp-sample-create-colnect.html', context)
