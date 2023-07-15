import time
from decimal import Decimal

from django.http import HttpResponseRedirect, HttpResponseForbidden, HttpResponseBadRequest
from django.shortcuts import render
from django.urls import reverse
from django.views import View
from django.views.decorators.http import require_http_methods
from django.views.generic import ListView

from .forms import CalcConfigForm, ColnectCreateForm, UserStampCreateForm, UserStampEditForm
from .models import StampSample, UserStamp, Desk, DeskType


def root_view(request):
    return HttpResponseRedirect(reverse('combinations:user-stamps'))


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
                StampSample.objects.from_colnect(url.strip())
                time.sleep(5)

    return HttpResponseRedirect(reverse('combinations:samples'))


class StampSampleColnectView(View):
    def get(self, request, *args, **kwargs):
        view = StampSampleListView.as_view()
        return view(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        view = samples_create_from_colnect_view
        return view(request, *args, **kwargs)


def user_stamps_list_view(request):
    if not request.user.is_authenticated:
        return HttpResponseForbidden()

    if request.method == 'POST':
        form = UserStampCreateForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            for _ in range(int(data['quantity'])):
                desk = Desk.objects.get(
                    user=request.user,
                    type=DeskType.AVAILABLE,
                )
                UserStamp.objects.create(
                    sample=data['sample'],
                    custom_name=data['custom_name'],
                    comment=data['comment'],
                    user=request.user,
                    desk=desk,
                )

    form = UserStampCreateForm(user=request.user)

    stamps = {}
    for stamp in UserStamp.objects.filter(user=request.user):
        if stamp.sample.name not in stamps:
            stamps[stamp.sample.name] = {
                'id': stamp.id,
                'sample': stamp.sample,
                'custom_name': stamp.custom_name,
                'comment': stamp.comment,
                'quantity': 0,
                'allow_repeat': stamp.allow_repeat,
            }
        stamps[stamp.sample.name]['quantity'] += 1

    context = {
        'stamps': stamps,
        'form_create': form,
    }

    return render(request, 'combinations/user-stamp-list.html', context)


def user_stamps_edit_view(request, stamp_id: int):
    stamp = UserStamp.objects.get(id=stamp_id)
    if not request.user.is_authenticated or stamp.user.id != request.user.id:
        return HttpResponseForbidden()

    init_stamps_count = UserStamp.objects.filter(
        user=stamp.user,
        sample=stamp.sample,
    ).count()

    if request.method == 'POST':
        form = UserStampEditForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            if data['quantity_change'] > 0:
                for _ in range(data['quantity_change']):
                    UserStamp.objects.create(
                        sample=stamp.sample,
                        user=request.user,
                        desk=Desk.desk_available(request.user),
                    )
            elif data['quantity_change'] < 0:
                if abs(data['quantity_change']) > init_stamps_count:
                    return HttpResponseBadRequest('Not enough stamps to remove')

                stamps_to_delete = UserStamp.objects.filter(
                    sample=stamp.sample,
                    user=request.user,
                )[:abs(data['quantity_change'])]
                for stamp in stamps_to_delete:
                    stamp.delete()

            UserStamp.objects.filter(
                sample=stamp.sample,
                user=request.user,
            ).update(
                custom_name=data['custom_name'],
                comment=data['comment'],
                allow_repeat=data['allow_repeat'],
            )

            return HttpResponseRedirect(reverse('combinations:user-stamps'))

    stamp.refresh_from_db()

    data = {
        'original_name': stamp.sample.name,
        'custom_name': stamp.custom_name,
        'comment': stamp.comment,
        'quantity': UserStamp.objects.filter(
            user=stamp.user,
            sample=stamp.sample,
        ).count(),
        'allow_repeat': stamp.allow_repeat,
    }
    form = UserStampEditForm(initial=data)

    context = {
        'stamp': stamp,
        'form': form,
    }

    return render(request, 'combinations/user-stamp-edit.html', context)


def combinations_view(request):
    combs = None
    if request.method == 'POST':
        if all(field in request.POST.keys() for field in CalcConfigForm.declared_fields):
            new_settings = {
                'stamps_count': int(request.POST['stamps_count']),
                'target_value': Decimal(request.POST['target_value']),
                'max_value': Decimal(request.POST['max_value']),
            }

            request.user.calc_settings = new_settings
            request.user.save()

        desk = Desk.desk_available(request.user)
        combs = desk.combinations()

    request.user.refresh_from_db()
    form = CalcConfigForm(initial=request.user.calc_settings)

    context = {
        'form': form,
        'combs': combs,
    }

    return render(request, 'combinations/combinations.html', context)
