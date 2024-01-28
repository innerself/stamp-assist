import threading
import time
from decimal import Decimal
from logging import getLogger
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponseRedirect, HttpResponseForbidden, HttpResponseBadRequest
from django.shortcuts import render
from django.urls import reverse
from django.views import View
from django.views.decorators.http import require_http_methods
from django.views.generic import ListView

from .forms import CalcConfigForm, ColnectCreateForm, UserStampCreateForm, UserStampEditForm, \
    UserStampAddForm
from .models import StampSample, UserStamp, Desk, DeskType

logger = getLogger()


def index_view(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse('combinations:combinations'))
    else:
        return HttpResponseRedirect(reverse('accounts:login'))


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
            urls = form.cleaned_data['urls'].split('\n')
            existing_urls = StampSample.objects.all().values_list('url', flat=True)
            for index, url in enumerate(urls, 1):
                print(f'Importing {index}/{len(urls)} sample', end='\r')
                url = url.strip()
                if url in existing_urls:
                    logger.warning(f'\nSample from URL: {url} already imported')
                    continue

                StampSample.objects.from_colnect_url(url)
                time.sleep(5)
            print('\n')

    return HttpResponseRedirect(reverse('combinations:samples'))


class StampSampleColnectView(View):
    def get(self, request, *args, **kwargs):
        view = StampSampleListView.as_view()
        return view(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        view = samples_create_from_colnect_view
        return view(request, *args, **kwargs)


@login_required
def stamp_samples_view(request):
    if not request.user.is_authenticated:
        return HttpResponseForbidden()

    if request.method == 'POST':
        form = ColnectCreateForm(request.POST)
        if form.is_valid():
            urls = form.cleaned_data['urls'].split('\n')
            existing_urls = StampSample.objects.all().values_list('url', flat=True)
            for index, url in enumerate(urls, 1):
                print(f'Importing {index}/{len(urls)} sample', end='\r')
                url = url.strip()
                if url in existing_urls:
                    logger.warning(f'\nSample from URL: {url} already imported')
                    continue

                thread = threading.Thread(
                    target=StampSample.objects.from_colnect_url,
                    args=(url, )
                )
                thread.start()
                thread.join()
                time.sleep(5)
            print('\n')

    form = ColnectCreateForm()

    user_sample_ids = list(set(x.sample.id for x in request.user.stamps.all()))
    context = {
        'form': form,
        'samples': StampSample.objects.all().exclude(id__in=user_sample_ids).order_by('value'),
    }

    return render(request, 'combinations/stamp-sample-list.html', context)


@login_required
def stamp_samples_add_view(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden('Only superusers can add samples')

    form = ColnectCreateForm()

    context = {'form': form}

    return render(request, 'combinations/stamp-sample-create-colnect.html', context)


def user_stamp_add_view(request, sample_id: int):
    if not request.user.is_authenticated:
        return HttpResponseForbidden()

    sample = StampSample.objects.get(id=sample_id)

    if request.method == 'POST':
        form = UserStampAddForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            desk = Desk.objects.get(
                user=request.user,
                type=DeskType.AVAILABLE,
            )
            for _ in range(int(data['quantity'])):
                UserStamp.objects.create(
                    sample=sample,
                    custom_name=data['custom_name'],
                    comment=data['comment'],
                    user=request.user,
                    desk=desk,
                )

            return HttpResponseRedirect(reverse('combinations:samples'))

    form = UserStampAddForm(initial={'original_name': sample.name})

    context = {
        'sample': sample,
        'form': form,
    }

    return render(request, 'combinations/user-stamp-add.html', context)


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
    for stamp in UserStamp.objects.filter(user=request.user).order_by('sample__value'):
        if stamp.sample.slug not in stamps:
            stamps[stamp.sample.slug] = {
                'id': stamp.id,
                'sample': stamp.sample,
                'custom_name': stamp.custom_name,
                'comment': stamp.comment,
                'quantity': 0,
                'allow_repeat': stamp.allow_repeat,
            }
        stamps[stamp.sample.slug]['quantity'] += 1

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
                'stamps_min': int(request.POST['stamps_min']),
                'stamps_max': int(request.POST['stamps_max']),
                'target_value': Decimal(request.POST['target_value']),
                'max_value': Decimal(request.POST['max_value']),
            }

            request.user.calc_settings = new_settings
            request.user.save()

        if stamp_id := request.POST.get('use_stamp'):
            stamp = UserStamp.objects.get(id=stamp_id)
            stamp.to_postcard()

            if not request.user.allow_stamp_repeat and not stamp.allow_repeat:
                UserStamp.objects \
                    .filter(user=request.user, sample=stamp.sample) \
                    .exclude(id=stamp_id) \
                    .update(desk=Desk.desk_removed(request.user))
        elif stamp_id := request.POST.get('remove_stamp'):
            stamp = UserStamp.objects.get(id=stamp_id)
            UserStamp.objects.filter(
                user=stamp.user,
                sample=stamp.sample,
            ).update(desk=Desk.desk_removed(request.user))
        elif 'reset' in request.POST:
            desk = Desk.desk_available(request.user)
            desk.clear_cache()
            UserStamp.objects \
                .filter(user=request.user) \
                .exclude(desk=desk) \
                .update(desk=desk)
            # return redirect(reverse('combinations:combinations'))

        if 'reset' not in request.POST:
            desk = Desk.desk_available(request.user)
            desk.clear_cache()
            combs = desk.combinations()
    else:
        desk = Desk.desk_available(request.user)
        combs = desk.combinations()

    if combs:
        paginator = Paginator(combs, 10)
        page = request.GET.get('page')

        try:
            p_combs = paginator.page(page)
        except PageNotAnInteger:
            p_combs = paginator.page(1)
        except EmptyPage:
            p_combs = paginator.page(paginator.num_pages)
    else:
        paginator = Paginator([], 10)
        p_combs = paginator.page(1)

    request.user.refresh_from_db()
    form = CalcConfigForm(initial=request.user.calc_settings)

    used_stamps = UserStamp.objects.filter(
        user=request.user,
        desk=Desk.desk_postcard(request.user),
    )
    used_stamps_ids = [x.sample.id for x in used_stamps]

    removed_stamps = set(
        x.sample
        for x in UserStamp.objects.filter(
            user=request.user,
            desk=Desk.desk_removed(request.user),
        ).exclude(sample_id__in=used_stamps_ids)
    )

    context = {
        'form': form,
        'combs': p_combs,
        'total_combs': len(combs) if combs else 0,
        'used_stamps': used_stamps,
        'removed_stamps': removed_stamps,
    }

    return render(request, 'combinations/combinations.html', context)


@require_http_methods(['POST'])
@login_required
def stick_stamps_to_postcard(request):
    UserStamp.objects.filter(
        user=request.user,
        desk=request.user.desks.get(type=DeskType.POSTCARD),
    ).delete()

    return HttpResponseRedirect(reverse('combinations:combinations'))
