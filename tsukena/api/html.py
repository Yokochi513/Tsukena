from fastapi.responses import HTMLResponse


def html_page(title: str, message: str, status_code: int = 200) -> HTMLResponse:
    # 文言はすべて呼び出す側のコードで決めたもので、外から受け取った値は入れない
    return HTMLResponse(
        f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} - Tsukena</title>
</head>
<body style="font-family: sans-serif; max-width: 32rem; margin: 3rem auto; padding: 0 1rem;">
<h1>{title}</h1>
<p>{message}</p>
</body>
</html>
""",
        status_code=status_code,
    )
