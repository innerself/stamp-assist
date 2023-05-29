from decimal import Decimal

from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views import View
from django.views.decorators.http import require_http_methods
from django.views.generic import CreateView, ListView

from accounts.models import User
from .forms import CalcConfigForm, ColnectCreateForm
from .models import StampCollection, StampSample


def root_view(request):
    if request.method == 'POST':
        if all(field in request.POST.keys() for field in CalcConfigForm.declared_fields):
            new_settings = {
                'stamps_count': int(request.POST['stamps_count']),
                'target_value': Decimal(request.POST['target_value']),
                'max_value': Decimal(request.POST['max_value']),
            }

            request.user.calc_settings = new_settings
            request.user.save()

    # combs = stamp_collection.combinations()

    request.user.refresh_from_db()
    form = CalcConfigForm(initial=request.user.calc_settings)

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

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = ColnectCreateForm()
        return context


@require_http_methods(['GET', 'POST'])
def samples_create_from_colnect_view(request):
    if request.method == 'POST':
        form = ColnectCreateForm(request.POST)
        if form.is_valid():
            for url in form.cleaned_data['urls'].split('\n'):
                StampSample.objects.from_colnect(url)

    return HttpResponseRedirect(reverse('combinations:samples-colnect'))


class StampSampleColnectView(View):
    def get(self, request, *args, **kwargs):
        view = StampSampleListView.as_view()
        return view(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        view = samples_create_from_colnect_view
        return view(request, *args, **kwargs)
