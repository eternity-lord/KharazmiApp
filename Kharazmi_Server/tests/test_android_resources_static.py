# test_android_resources_static.py
# گاردهای ایستا برای منابع اپ اندروید (KharazmiAdmin) — چون در این محیط Gradle/JDK نیست و
# `assembleDebug` اجرا نمی‌شود، این تست‌ها همان خطاهایی را می‌گیرند که «Resource and asset merger»
# یا aapt2 هنگام build می‌گیرد:
#   ۱) نام تکراری در یک فایل `values*/strings.xml`  ⇒ خطای واقعی build:
#      «Found item String/<name> more than one time»
#   ۲) هر `R.string.X` استفاده‌شده در Kotlin باید در `values/strings.xml` تعریف شده باشد.
#   ۳) تعداد/نوع آرگومان‌های `getString(R.string.X, …)` باید با placeholderهای رشته بخواند
#      (وگرنه در زمان اجرا MissingFormatArgumentException).
#   ۴) هر `R.<نوع>.<نام>` استفاده‌شده در Kotlin باید منبع متناظر داشته باشد (لینک R).
#
# انگیزهٔ واقعی: باگ build «attendance_server_error دو بار تعریف شده بود» (یک بار با ۲ آرگومان و
# یک بار با ۱ آرگومان) که mergeDebugResources را می‌شکست.
import os
import re
import unittest
import xml.etree.ElementTree as ET

SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(SERVER_DIR)
ANDROID_MAIN = os.path.join(REPO_ROOT, "KharazmiAdmin", "app", "src", "main")
RES_DIR = os.path.join(ANDROID_MAIN, "res")
JAVA_DIR = os.path.join(ANDROID_MAIN, "java")

# نوع‌های منابعی که aapt2 برای هر پوشهٔ res تولید می‌کند (برای چک لینک R)
RES_FOLDERS = {
    "layout": "layout", "drawable": "drawable", "mipmap": "mipmap-anydpi-v26", "font": "font",
    "anim": "anim", "color": "color", "menu": "menu", "xml": "xml", "raw": "raw",
}


def _strip_comments(source: str) -> str:
    """کامنت‌های کاتلینی/بلوکی را حذف می‌کند تا اسکن روی کد واقعی باشد، نه توضیحات."""
    source = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), source, flags=re.S)
    return re.sub(r"^\s*//.*$", "", source, flags=re.M)


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def _strings_files():
    return sorted(
        os.path.join(RES_DIR, folder, "strings.xml")
        for folder in os.listdir(RES_DIR)
        if folder.startswith("values") and os.path.exists(os.path.join(RES_DIR, folder, "strings.xml"))
    )


def _string_entries(path):
    """[(نام, متن)] از یک فایل strings.xml — با xml.etree."""
    root = ET.parse(path).getroot()
    return [(el.get("name"), "".join(el.itertext())) for el in root if el.tag == "string" and el.get("name")]


def _placeholders(text: str):
    """تعداد/ترتیب placeholderهای یک رشتهٔ فرمت‌دار اندروید.

    • positional مثل `%1$d` / `%2$s` / `%1$.2f` ⇒ نوع‌ها به ترتیب شماره
    • غیر-positional مثل `%,d` (جداکنندهٔ هزارگان، همان الگوی `common_toman_format`) ⇒ یک آرگومان
    • `%%` (درصد خام) شمرده نمی‌شود.
    """
    positional = {int(m.group(1)): m.group(2).rstrip(".") for m in re.finditer(r"%(\d+)\$([a-zA-Z.]+)", text)}
    if positional:
        return [kind for _index, kind in sorted(positional.items())]
    without_escapes = text.replace("%%", "")
    return ["arg"] * len(re.findall(r"%[-#+ 0,(]*\d*(?:\.\d+)?[a-zA-Z]", without_escapes))


def _string_format_arg_spans(source: str):
    """بازه‌های متنی که آرگومان‌های `String.format(...)` هستند.

    چرا لازم است: الگوی رایج و درست `String.format(Locale.US, getString(R.string.X), value)` هم
    وجود دارد؛ آنجا `getString` عمداً بدون آرگومان صدا زده می‌شود و `String.format` placeholder
    را پر می‌کند ⇒ نباید ناسازگاری شمرده شود.
    """
    spans = []
    for match in re.finditer(r"String\.format\s*\(", source):
        index = match.end()
        depth = 1
        while index < len(source) and depth > 0:
            char = source[index]
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            index += 1
        spans.append((match.end(), index))
    return spans


def _kotlin_files():
    for root_dir, _dirs, files in os.walk(JAVA_DIR):
        for name in sorted(files):
            if name.endswith((".kt", ".java")):
                yield os.path.join(root_dir, name)


class TestAndroidStringResources(unittest.TestCase):
    """گاردهای ۱ و ۲ — خطاهای قطعی build."""

    def test_1_no_duplicate_string_names_in_any_values_file(self):
        """همان خطای واقعی build: «Found item String/<name> more than one time»."""
        offenders = {}
        files = _strings_files()
        self.assertTrue(files, f"هیچ values*/strings.xml پیدا نشد زیر {RES_DIR}")
        for path in files:
            seen = {}
            for name, _text in _string_entries(path):
                seen[name] = seen.get(name, 0) + 1
            dups = sorted(name for name, count in seen.items() if count > 1)
            if dups:
                offenders[os.path.relpath(path, REPO_ROOT)] = dups
        self.assertEqual(offenders, {}, f"نام رشتهٔ تکراری (build می‌شکند): {offenders}")

    def test_1b_no_duplicate_resource_names_in_any_res_file(self):
        """همین خطا برای رنگ/دایمن/استایل/آی‌دی هم build را می‌شکند — کل پوشهٔ res اسکن می‌شود."""
        offenders = {}
        for root_dir, _dirs, names in os.walk(RES_DIR):
            for name in sorted(names):
                if not name.endswith(".xml"):
                    continue
                path = os.path.join(root_dir, name)
                try:
                    root = ET.parse(path).getroot()
                except ET.ParseError as error:  # XML خراب ⇒ خودش خطای build است
                    offenders[os.path.relpath(path, REPO_ROOT)] = [f"XML نامعتبر: {error}"]
                    continue
                per_tag = {}
                for el in root:
                    key = el.get("name")
                    if not key:
                        continue
                    per_tag.setdefault(el.tag, {})[key] = per_tag.get(el.tag, {}).get(key, 0) + 1
                for tag, counts in per_tag.items():
                    dups = sorted(k for k, v in counts.items() if v > 1)
                    if dups:
                        offenders.setdefault(os.path.relpath(path, REPO_ROOT), []).append(f"{tag}: {dups}")
        self.assertEqual(offenders, {}, f"نام منبع تکراری در یک فایل (build می‌شکند): {offenders}")

    def test_2_every_used_string_key_is_defined(self):
        """هر R.string.X در Kotlin باید در values/strings.xml تعریف شده باشد."""
        defined = {name for name, _text in _string_entries(os.path.join(RES_DIR, "values", "strings.xml"))}
        offenders = {}
        for path in _kotlin_files():
            source = _strip_comments(_read(path))
            for match in re.finditer(r"(?<![\w.])R\.string\.([A-Za-z_][A-Za-z0-9_]*)", source):
                if match.group(1) not in defined:
                    offenders.setdefault(os.path.relpath(path, REPO_ROOT), set()).add(match.group(1))
        self.assertEqual(offenders, {}, f"کلید رشتهٔ تعریف‌نشده: {offenders}")

    def test_3_getstring_arguments_match_placeholders(self):
        """تعداد آرگومان‌های getString باید با placeholderهای همان رشته بخواند."""
        defs = {}
        for path in _strings_files():
            for name, text in _string_entries(path):
                defs.setdefault(name, []).append(text)
        call_re = re.compile(r"getString\(\s*R\.string\.([A-Za-z_][A-Za-z0-9_]*)\s*(,)?")
        offenders = []
        for path in _kotlin_files():
            source = _strip_comments(_read(path))
            format_spans = _string_format_arg_spans(source)
            for match in call_re.finditer(source):
                name = match.group(1)
                if name not in defs:
                    continue  # گارد تعریف‌نشده‌ها در تست ۲
                if not match.group(2):
                    n_args = 0
                else:
                    # شمارش آرگومان‌ها تا پرانتز بستهٔ متناظر (با احتساب پرانتزهای تودرتو)
                    index, depth, buffer, args = match.end(), 1, "", []
                    while index < len(source) and depth > 0:
                        char = source[index]
                        if char == "(":
                            depth += 1
                            buffer += char
                        elif char == ")":
                            depth -= 1
                            if depth == 0:
                                break
                            buffer += char
                        elif char == "," and depth == 1:
                            args.append(buffer)
                            buffer = ""
                        else:
                            buffer += char
                        index += 1
                    if buffer.strip():
                        args.append(buffer)
                    n_args = len([a for a in args if a.strip()])
                expected = {len(_placeholders(text)) for text in defs[name]}
                # getString بدون آرگومان داخل String.format(...) درست است (پُر شدن بیرونی placeholder)
                wrapped_in_format = n_args == 0 and any(start <= match.start() < end for start, end in format_spans)
                if n_args not in expected and not wrapped_in_format:
                    line = source[: match.start()].count("\n") + 1
                    offenders.append(
                        f"{os.path.relpath(path, REPO_ROOT)}:{line} → R.string.{name} "
                        f"args={n_args} ولی placeholder={sorted(expected)}"
                    )
        self.assertEqual(offenders, [], "ناسازگاری آرگومان/placeholder:\n" + "\n".join(offenders))

    def test_4_r_references_resolve_to_real_resources(self):
        """لینک R: هر R.<نوع>.<نام> در Kotlin باید منبع متناظر در res داشته باشد."""
        defined = {}
        for folder in os.listdir(RES_DIR):
            if not folder.startswith("values"):
                continue
            for name in os.listdir(os.path.join(RES_DIR, folder)):
                if not name.endswith(".xml"):
                    continue
                try:
                    root = ET.parse(os.path.join(RES_DIR, folder, name)).getroot()
                except ET.ParseError:  # pragma: no cover - فایل XML خراب، در جای دیگری دیده می‌شود
                    continue
                for el in root:
                    key = el.get("name")
                    if not key:
                        continue
                    if el.tag in ("string", "plurals", "string-array"):
                        defined.setdefault("string", set()).add(key)
                    elif el.tag == "color":
                        defined.setdefault("color", set()).add(key)
                    elif el.tag == "dimen":
                        defined.setdefault("dimen", set()).add(key)
                    elif el.tag == "style":
                        defined.setdefault("style", set()).add(key.replace(".", "_"))
                    elif el.tag == "item" and el.get("type"):
                        defined.setdefault(el.get("type"), set()).add(key)
        for kind, folder in RES_FOLDERS.items():
            if not os.path.isdir(os.path.join(RES_DIR, folder)):
                continue
            for name in os.listdir(os.path.join(RES_DIR, folder)):
                defined.setdefault(kind, set()).add(os.path.splitext(name)[0])
        # شناسه‌ها (R.id.*) از layout/menu/xml ساخته می‌شوند — aapt2 همان‌ها را تولید می‌کند.
        id_sources = []
        for folder in os.listdir(RES_DIR):
            if folder.startswith(("layout", "menu", "xml", "anim")) or folder.startswith("values"):
                folder_path = os.path.join(RES_DIR, folder)
                if os.path.isdir(folder_path):
                    id_sources.extend(os.path.join(folder_path, n) for n in os.listdir(folder_path) if n.endswith(".xml"))
        for path in id_sources:
            try:
                source = _read(path)
            except OSError:  # pragma: no cover
                continue
            defined.setdefault("id", set()).update(re.findall(r"@\+?id/([A-Za-z_][A-Za-z0-9_]*)", source))

        offenders = []
        for path in _kotlin_files():
            source = _strip_comments(_read(path))
            for match in re.finditer(r"(?<![\w.])R\.([a-z]+)\.([A-Za-z_][A-Za-z0-9_]*)", source):
                kind, name = match.group(1), match.group(2)
                if kind not in defined:
                    continue
                if name not in defined[kind]:
                    line = source[: match.start()].count("\n") + 1
                    offenders.append(f"{os.path.relpath(path, REPO_ROOT)}:{line} → R.{kind}.{name}")
        self.assertEqual(offenders, [], "ارجاع R بدون منبع:\n" + "\n".join(offenders))


class TestAttendanceServerErrorRegression(unittest.TestCase):
    """گارد رگرسیون همان باگ build: کلید تکراری در AttendanceActivity."""

    def test_two_distinct_error_keys_with_correct_arity(self):
        """پیام «خطای سرور با جزئیات» (۲ آرگومان) و «۵۰۰ با پیام تلاش مجدد» (۱ آرگومان) هر دو
        باید باشند ولی با **کلیدهای متفاوت** — قبلاً هر دو `attendance_server_error` بودند و
        mergeDebugResources را می‌شکستند."""
        defs = dict(_string_entries(os.path.join(RES_DIR, "values", "strings.xml")))
        self.assertIn("attendance_server_error", defs)
        self.assertNotIn(None, defs)
        self.assertTrue("attendance_server_error_retry" in defs,
                        "کلید `attendance_server_error_retry` تعریف نشده (باگ build: کلید تکراری)")
        self.assertEqual(_placeholders(defs["attendance_server_error"]), ["d", "s"],
                         "پیام اصلی باید (%1$d): %2$s باشد")
        self.assertEqual(_placeholders(defs["attendance_server_error_retry"]), ["d"],
                         "پیام ریتِرای باید تک‌آرگومانی باشد")

        source = _strip_comments(_read(os.path.join(JAVA_DIR, "com", "example", "kharazmiadmin",
                                                    "AttendanceActivity.kt")))
        # فراخوانی دوعملوندی (سمت بارگذاری کلیدهای حضور) روی پیام اصلی مانده است
        self.assertRegex(source, r"R\.string\.attendance_server_error,\s*e\.code\(\),\s*detail",
                         "فراخوانی ۲-آرگومانی باید از کلید اصلی استفاده کند")
        # فراخوانی تک‌آرگومانی (۵۰۰..۵۹۹ در ثبت جلسه) باید به کلید retry منتقل شده باشد
        self.assertRegex(source, r"R\.string\.attendance_server_error_retry,\s*e\.code\(\)",
                         "فراخوانی ۱-آرگومانی باید از کلید retry استفاده کند")


if __name__ == "__main__":
    unittest.main()
