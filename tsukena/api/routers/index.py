from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from ..html import html_page

router = APIRouter()


# 外から URL だけを見に来た人（セキュリティ製品の審査を含む）に、何のサーバーかを示す（→ docs/api_list.md 2.9）
@router.get("/", response_class=HTMLResponse)
def index():
    return html_page(
        "このサーバーについて",
        "Tsukena は、個人が自分ひとりで使う家計簿アプリのサーバー（API）です。"
        "スマホアプリと Discord の bot だけが、トークンを付けて呼び出します。"
        "利用者の登録や、外部の方が使える機能はありません。",
    )
