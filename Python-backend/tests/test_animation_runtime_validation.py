from app.agents.animation_skill_generator import _validate_animation_html_contract


def test_animation_contract_accepts_stage_and_active_beat():
    html = """<!doctype html>
<html>
<head>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
  <script>const beats = document.querySelectorAll('.beat');</script>
</head>
<body>
  <main id="stage">
    <section class="beat active">第一屏</section>
    <section class="beat">第二屏</section>
  </main>
</body>
</html>"""
    ok, error = _validate_animation_html_contract(html)
    assert ok is True
    assert error == ""


def test_animation_contract_rejects_missing_beat():
    html = "<!doctype html><html><body><main id='stage'>空白</main></body></html>"
    ok, error = _validate_animation_html_contract(html)
    assert ok is False
    assert ".beat" in error


def test_animation_contract_rejects_missing_stage():
    html = "<!doctype html><html><body><section class='beat active'>内容</section></body></html>"
    ok, error = _validate_animation_html_contract(html)
    assert ok is False
    assert "#stage" in error
