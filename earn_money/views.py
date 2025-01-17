from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Video, Wallet, Transaction

@login_required
def video_list(request):
    videos = Video.objects.all()
    return render(request, 'earn_money/video_list.html', {'videos': videos})

@login_required
def watch_video(request, video_id):
    video = Video.objects.get(id=video_id)
    wallet = Wallet.objects.get(user=request.user)
    wallet.balance += video.reward
    wallet.save()
    Transaction.objects.create(wallet=wallet, amount=video.reward, is_withdrawal=False)
    return redirect('video_list')

@login_required
def wallet(request):
    wallet = Wallet.objects.get(user=request.user)
    transactions = Transaction.objects.filter(wallet=wallet)
    return render(request, 'earn_money/wallet.html', {'wallet': wallet, 'transactions': transactions})

@login_required
def withdraw(request):
    if request.method == "POST":
        wallet = Wallet.objects.get(user=request.user)
        amount = float(request.POST.get('amount'))
        if amount <= wallet.balance:
            wallet.balance -= amount
            wallet.save()
            Transaction.objects.create(wallet=wallet, amount=-amount, is_withdrawal=True)
            # Add payment gateway integration here
        return redirect('wallet')
    return render(request, 'earn_money/withdraw.html')
