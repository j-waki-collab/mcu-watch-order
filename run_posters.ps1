# TMDBのトークンを聞いて、ポスター取得スクリプトを動かします
Set-Location -Path $PSScriptRoot
Write-Host ""
Write-Host "TMDBの「APIリードアクセストークン」か「APIキー」を貼り付けてEnterを押してください。"
Write-Host "（入力した文字は画面に表示されません）"
$secure = Read-Host "トークン" -AsSecureString
$env:TMDB_TOKEN = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure))
python fetch_posters.py
Remove-Item Env:TMDB_TOKEN
Write-Host ""
Read-Host "終わりました。Enterで閉じます"
