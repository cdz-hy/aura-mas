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


def test_animation_contract_accepts_beat_when_not_first_class_token():
    html = """<!doctype html>
<html>
<head>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
</head>
<body>
  <main id="stage">
    <section class="scene beat active">第一屏</section>
  </main>
</body>
</html>"""
    ok, error = _validate_animation_html_contract(html)
    assert ok is True
    assert error == ""


def test_animation_contract_accepts_stage_id_with_attribute_spacing():
    html = """<!doctype html>
<html>
<head>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
</head>
<body>
  <main id = "stage">
    <section class="beat active">第一屏</section>
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


def test_animation_contract_rejects_active_outside_beat_element():
    html = """<!doctype html>
<html>
<head>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
  <script>const active = true;</script>
</head>
<body>
  <main id="stage">
    <section class="beat">内容</section>
    <div class="active">不是 beat</div>
  </main>
</body>
</html>"""
    ok, error = _validate_animation_html_contract(html)
    assert ok is False
    assert "active beat" in error


def test_animation_contract_rejects_class_text_inside_comments_or_scripts():
    html = """<!doctype html>
<html>
<head>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
  <script>const ghost = '<section class="beat active">假的</section>';</script>
</head>
<body>
  <main id="stage">
    <!-- <section class="beat active">假的</section> -->
    <p>没有真实 beat 元素</p>
  </main>
</body>
</html>"""
    ok, error = _validate_animation_html_contract(html)
    assert ok is False
    assert ".beat" in error


def test_animation_contract_rejects_inline_gsap_without_script_reference():
    html = """<!doctype html>
<html>
<head>
  <script>gsap.to('.beat', { opacity: 1 });</script>
</head>
<body>
  <main id="stage">
    <section class="beat active">第一屏</section>
  </main>
</body>
</html>"""
    ok, error = _validate_animation_html_contract(html)
    assert ok is False
    assert "GSAP" in error
