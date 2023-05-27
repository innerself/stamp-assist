from decimal import Decimal

from django.shortcuts import render

from accounts.models import User
from .forms import CalcConfigForm
from .models import  StampCollection


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
