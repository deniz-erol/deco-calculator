"""Minimal i18n layer for the Streamlit UI: English/Turkish string table,
a ``t()`` lookup helper, and a sidebar language toggle.

Deliberately import-light (streamlit only) so every other UI module can
import from here without risking a circular import with ``app._shared``.
Nothing here talks to the engine or the filesystem.
"""

from __future__ import annotations

import streamlit as st

LANG_KEY = "lang"
LANGUAGES = {"en": "English", "tr": "Türkçe"}
DEFAULT_LANG = "en"

# key -> {"en": "...", "tr": "..."}
TRANSLATIONS: dict[str, dict[str, str]] = {
    # --- Sidebar / language & units ---
    "language_label": {"en": "Language", "tr": "Dil"},
    "units_label": {"en": "Display units", "tr": "Birimler"},
    "units_feet": {"en": "Feet (fsw)", "tr": "Fit (fsw)"},
    "units_meters": {"en": "Meters", "tr": "Metre"},
    # --- Disclaimer ---
    "disclaimer_text": {
        "en": (
            "**Academic prototype for a thesis presentation.** This tool reproduces "
            "US Navy Diving Manual (Rev 7) decompression *tables* for demonstration "
            "only. It is **NOT** a certified dive-planning tool and must **never** "
            "be used for operational dive planning. Decompression errors can cause "
            "serious injury or death — always plan real dives with certified "
            "software, current manuals, and qualified supervision."
        ),
        "tr": (
            "**Tez sunumu için akademik prototip.** Bu araç, yalnızca gösterim "
            "amacıyla US Navy Diving Manual (Rev 7) dekompresyon *tablolarını* "
            "yeniden üretir. Sertifikalı bir dalış planlama aracı **DEĞİLDİR** ve "
            "operasyonel dalış planlamasında **kesinlikle** kullanılmamalıdır. "
            "Dekompresyon hataları ciddi yaralanmaya veya ölüme yol açabilir — "
            "gerçek dalışları her zaman sertifikalı yazılımlar, güncel kılavuzlar "
            "ve yetkili gözetim eşliğinde planlayın."
        ),
    },
    # --- Data-provenance banner (render_result_warnings) ---
    "provenance_banner": {
        "en": (
            "**Table data is NOT verified — never use it for real dive "
            "planning.** All tables are transcribed from the official US "
            "Navy Diving Manual Rev 7 tables (air 9-7/9-8/9-9, heliox 12-4) "
            "or formula-derived (nitrox 10-1 EAD), but are still pending a "
            "final manual cell-by-cell spot-check — every table is marked "
            "`verified: false`. Verify every value against a physical manual "
            "before any real use."
        ),
        "tr": (
            "**Tablo verileri doğrulanmamıştır — gerçek dalış planlamasında "
            "asla kullanmayın.** Tüm tablolar ya resmi US Navy Diving Manual "
            "Rev 7 tablolarından aktarılmıştır (hava 9-7/9-8/9-9, helioks "
            "12-4) ya da formülle türetilmiştir (nitroks 10-1 EAD), ancak "
            "kılavuzla hücre hücre nihai bir kontrol hâlâ beklemektedir — her "
            "tablo `verified: false` olarak işaretlidir. Gerçek kullanımdan "
            "önce her değeri fiziksel bir kılavuzla doğrulayın."
        ),
    },
    # --- Home page ---
    "home_page_title": {
        "en": "US Navy Decompression Table Calculator",
        "tr": "US Navy Dekompresyon Tablosu Hesaplayıcı",
    },
    "home_intro": {
        "en": (
            "This tool reproduces **US Navy Diving Manual (Rev 7)** decompression *tables*\n"
            "— no algorithm, no gas-switching engine, just faithful table lookups — for:\n\n"
            "- **Air** dives (no-decompression limits + decompression schedules)\n"
            "- **Nitrox** dives, via the Equivalent Air Depth (EAD) method\n"
            "- **Heliox** dives (surface-supplied mixed-gas schedules)\n"
            "- **Repetitive (consecutive) dive series**, chained through the\n"
            "  surface-interval / residual-nitrogen-time tables\n"
            "- **Saved profiles**, so a user can build and revisit dive series\n\n"
            "It exists to make the *tables themselves* legible and testable — every\n"
            "number traces back to a specific table, page, and (eventually) a\n"
            "cell-by-cell verified transcription. See **About** for sources and method\n"
            "notes."
        ),
        "tr": (
            "Bu araç, **US Navy Diving Manual (Rev 7)** dekompresyon *tablolarını*\n"
            "— algoritma yok, gaz geçiş motoru yok, sadece sadık tablo sorguları —\n"
            "şunlar için yeniden üretir:\n\n"
            "- **Hava** dalışları (dekompresyonsuz sınırlar + dekompresyon çizelgeleri)\n"
            "- **Nitroks** dalışları, Eşdeğer Hava Derinliği (EAD) yöntemiyle\n"
            "- **Helioks** dalışları (yüzeyden beslemeli karışık gaz çizelgeleri)\n"
            "- **Tekrarlı (ardışık) dalış serileri**, yüzey aralığı / artık azot "
            "süresi tabloları üzerinden zincirlenir\n"
            "- **Kaydedilmiş profiller**, böylece bir kullanıcı dalış serileri "
            "oluşturup tekrar inceleyebilir\n\n"
            "Amacı, *tabloların kendisini* okunabilir ve test edilebilir kılmaktır — "
            "her sayı belirli bir tabloya, sayfaya ve (nihayetinde) hücre hücre "
            "doğrulanmış bir transkripsiyona dayanır. Kaynaklar ve yöntem notları "
            "için **Hakkında** sayfasına bakın."
        ),
    },
    "home_get_started": {"en": "Get started", "tr": "Başlarken"},
    "home_link_plan_dive": {"en": "Plan a single dive", "tr": "Tek dalış planla"},
    "home_link_dive_series": {"en": "Build a dive series", "tr": "Dalış serisi oluştur"},
    "home_link_profiles": {"en": "Profiles", "tr": "Profiller"},
    "home_link_about": {"en": "About & sources", "tr": "Hakkında ve kaynaklar"},
    "home_footer_caption": {
        "en": (
            "Use the sidebar to navigate. The feet/meters display toggle and the "
            "safety disclaimer are available on every page."
        ),
        "tr": (
            "Gezinmek için kenar çubuğunu kullanın. Fit/metre birim seçici ve "
            "güvenlik uyarısı her sayfada mevcuttur."
        ),
    },
    # --- Plan Dive page ---
    "plan_dive_page_title": {"en": "Plan a Single Dive", "tr": "Tek Dalış Planla"},
    "plan_dive_sidebar_caption": {
        "en": "This page plans one standalone dive. For chained repetitive dives, use **Dive Series**.",
        "tr": "Bu sayfa tek bir bağımsız dalış planlar. Zincirlenmiş tekrarlı dalışlar için **Dalış Serisi**'ni kullanın.",
    },
    "dive_parameters_header": {"en": "Dive parameters", "tr": "Dalış parametreleri"},
    "slider_step_label": {"en": "Slider step size", "tr": "Kaydırıcı adım boyutu"},
    "slider_step_help": {
        "en": "Increment used by the depth and bottom-time sliders.",
        "tr": "Derinlik ve dip süresi kaydırıcılarında kullanılan artış miktarı.",
    },
    "gas_label": {"en": "Gas", "tr": "Gaz"},
    "gas_air": {"en": "Air", "tr": "Hava"},
    "gas_nitrox": {"en": "Nitrox (EAN)", "tr": "Nitroks (EAN)"},
    "gas_heliox": {"en": "Heliox", "tr": "Helioks"},
    "o2_pct_nitrox_label": {"en": "O2 % (nitrox)", "tr": "O2 % (nitroks)"},
    "o2_pct_nitrox_help": {
        "en": "Navy-authorized nitrox range is 25%-40% O2 (EAD method, Table 10-1).",
        "tr": "Donanma tarafından onaylı nitroks aralığı %25-%40 O2'dir (EAD yöntemi, Tablo 10-1).",
    },
    "heliox_load_error": {
        "en": "Could not load the heliox table: {error}",
        "tr": "Helioks tablosu yüklenemedi: {error}",
    },
    "heliox_depth_label": {
        "en": "{depth_label} (Table 12-4 rows only)",
        "tr": "{depth_label} (yalnızca Tablo 12-4 satırları)",
    },
    "heliox_depth_help": {
        "en": (
            "Heliox depth is picked from the seeded Table 12-4 rows so the "
            "O2 window is known up front."
        ),
        "tr": (
            "Helioks derinliği, O2 penceresinin önceden bilinmesi için "
            "hazır Tablo 12-4 satırlarından seçilir."
        ),
    },
    "heliox_o2_window_caption": {
        "en": "O2 window at this depth: **Min {min_o2:.1f}% – Max {max_o2:.1f}%**",
        "tr": "Bu derinlikteki O2 penceresi: **Min %{min_o2:.1f} – Maks %{max_o2:.1f}**",
    },
    "heliox_o2_mix_label": {"en": "O2 % (heliox mix)", "tr": "O2 % (helioks karışımı)"},
    "depth_label_ft": {"en": "Depth (fsw)", "tr": "Derinlik (fsw)"},
    "depth_label_m": {"en": "Depth (m)", "tr": "Derinlik (m)"},
    "bottom_time_label": {"en": "Bottom time (min)", "tr": "Dip süresi (dk)"},
    "invalid_dive_params_error": {
        "en": "Invalid dive parameters: {error}",
        "tr": "Geçersiz dalış parametreleri: {error}",
    },
    "plan_dive_engine_error": {
        "en": (
            "Could not plan this dive with the seeded table data: {error}\n\n"
            "Try a depth/time combination closer to the seeded ranges "
            "(see **About** for coverage notes)."
        ),
        "tr": (
            "Bu dalış, mevcut tablo verileriyle planlanamadı: {error}\n\n"
            "Mevcut aralıklara daha yakın bir derinlik/süre kombinasyonu deneyin "
            "(kapsam notları için **Hakkında** sayfasına bakın)."
        ),
    },
    "result_summary_header": {"en": "Result summary", "tr": "Sonuç özeti"},
    "status_label": {"en": "Status", "tr": "Durum"},
    "status_no_deco": {"en": "No-decompression", "tr": "Dekompresyon gerektirmez"},
    "status_deco_required": {"en": "Decompression required", "tr": "Dekompresyon gerekli"},
    "status_deco": {"en": "Decompression", "tr": "Dekompresyon"},
    "ndl_label": {"en": "NDL (min)", "tr": "Dekompresyonsuz sınır (NDL) (dk)"},
    "time_to_first_stop_label": {
        "en": "Time to first stop (min)",
        "tr": "İlk durağa kadar süre (dk)",
    },
    "repetitive_group_label": {"en": "Repetitive group", "tr": "Tekrar grubu"},
    "ending_group_label": {"en": "Ending group", "tr": "Bitiş grubu"},
    "not_applicable": {"en": "N/A", "tr": "Yok"},
    "total_stop_time_label": {"en": "Total stop time (min)", "tr": "Toplam durak süresi (dk)"},
    "rnt_applied_label": {"en": "RNT applied (min)", "tr": "Uygulanan artık azot süresi (dk)"},
    "residual_nitrogen_time_label": {
        "en": "Residual nitrogen time (min)",
        "tr": "Artık azot süresi (dk)",
    },
    "table_source_label": {"en": "Table source", "tr": "Tablo kaynağı"},
    "nitrox_ead_info": {
        "en": (
            "Actual depth: **{actual_depth}** · "
            "Equivalent Air Depth (EAD): **{ead_depth}** "
            "— the air tables were consulted at the EAD, not the actual depth."
        ),
        "tr": (
            "Gerçek derinlik: **{actual_depth}** · "
            "Eşdeğer Hava Derinliği (EAD): **{ead_depth}** "
            "— hava tabloları gerçek derinlikte değil, EAD'de kullanıldı."
        ),
    },
    "heliox_gas_phases_info": {
        "en": "Gas phases used in this schedule: **{phases}**",
        "tr": "Bu çizelgede kullanılan gaz aşamaları: **{phases}**",
    },
    "decompression_schedule_header": {
        "en": "Decompression schedule",
        "tr": "Dekompresyon çizelgesi",
    },
    "col_stop_depth": {"en": "Stop depth", "tr": "Durak derinliği"},
    "col_minutes": {"en": "Minutes", "tr": "Dakika"},
    "col_gas_phase": {"en": "Gas phase", "tr": "Gaz aşaması"},
    "no_deco_stops_success": {
        "en": "No decompression stops required — this is a no-decompression dive.",
        "tr": "Dekompresyon durağı gerekmez — bu dekompresyonsuz bir dalıştır.",
    },
    "no_deco_stops_success_short": {
        "en": "No decompression stops required.",
        "tr": "Dekompresyon durağı gerekmez.",
    },
    "dive_profile_header": {"en": "Dive profile", "tr": "Dalış profili"},
    "drag_hint_with_depth": {
        "en": "Drag a small box on the chart to set bottom time and depth — the sliders above will update.",
        "tr": "Dip süresini ve derinliği ayarlamak için grafik üzerinde küçük bir kutu sürükleyin — yukarıdaki kaydırıcılar güncellenecektir.",
    },
    "drag_hint_no_depth": {
        "en": (
            "Drag a small box on the chart to set bottom time (depth is fixed to "
            "the table row for heliox) — the sliders above will update."
        ),
        "tr": (
            "Dip süresini ayarlamak için grafik üzerinde küçük bir kutu sürükleyin "
            "(helioks için derinlik tablo satırına sabittir) — yukarıdaki kaydırıcılar "
            "güncellenecektir."
        ),
    },
    "chart_drag_tip": {
        "en": "Tip: drag across the chart to set depth & bottom time.",
        "tr": "İpucu: derinlik ve dip süresini ayarlamak için grafik üzerinde sürükleyin.",
    },
    "idealized_plan_caption": {
        "en": (
            "Idealized plan the US Navy table assumes: maximum depth for the entire "
            "bottom time, then a defined ascent with any required stops — not a "
            "recording of an actual dive."
        ),
        "tr": (
            "US Navy tablosunun varsaydığı idealize edilmiş plan: tüm dip süresi "
            "boyunca maksimum derinlik, ardından gerekli duraklarla tanımlı bir "
            "çıkış — gerçek bir dalışın kaydı değildir."
        ),
    },
    # --- Chart (_chart.py) ---
    "chart_time_axis": {"en": "Elapsed time (min)", "tr": "Geçen süre (dk)"},
    "chart_tooltip_time": {"en": "Time (min)", "tr": "Süre (dk)"},
    "chart_tooltip_phase": {"en": "Phase", "tr": "Aşama"},
    "chart_title": {"en": "Planned decompression profile", "tr": "Planlanan dekompresyon profili"},
    "chart_subtitle": {
        "en": "Square-profile assumption per the US Navy tables — not a recorded dive trace",
        "tr": "US Navy tablolarına göre kare-profil varsayımı — kaydedilmiş bir dalış izi değildir",
    },
    # --- Dive Series page ---
    "dive_series_page_title": {
        "en": "Dive Series (Repetitive Dives)",
        "tr": "Dalış Serisi (Tekrarlı Dalışlar)",
    },
    "dive_series_sidebar_caption": {
        "en": (
            "Air/nitrox dives chain through the surface-interval / residual-"
            "nitrogen-time tables (9-8). Heliox has no repetitive-group system and "
            "is always planned standalone, even inside a series."
        ),
        "tr": (
            "Hava/nitroks dalışları yüzey aralığı / artık azot süresi tabloları "
            "(9-8) üzerinden zincirlenir. Helioks'ta tekrar grubu sistemi yoktur "
            "ve bir seri içinde bile her zaman bağımsız olarak planlanır."
        ),
    },
    "build_series_header": {"en": "Build the series", "tr": "Seriyi oluştur"},
    "build_series_caption": {
        "en": "Add dives in order. The first dive has no surface interval; every subsequent dive needs one.",
        "tr": "Dalışları sırayla ekleyin. İlk dalışın yüzey aralığı yoktur; sonraki her dalış için bir yüzey aralığı gerekir.",
    },
    "o2_pct_label": {"en": "O2 %", "tr": "O2 %"},
    "o2_pct_heliox_label": {"en": "O2 % (heliox)", "tr": "O2 % (helioks)"},
    "o2_pct_air_display": {"en": "21 (air)", "tr": "21 (hava)"},
    "surface_interval_before_label": {
        "en": "Surface interval before (min)",
        "tr": "Öncesindeki yüzey aralığı (dk)",
    },
    "surface_interval_before_help": {
        "en": "Disabled for the first dive of a series (no prior dive).",
        "tr": "Serinin ilk dalışı için devre dışıdır (önceki dalış yok).",
    },
    "add_dive_button": {"en": "Add dive to series", "tr": "Seriye dalış ekle"},
    "invalid_gas_mix_error": {"en": "Invalid gas mix: {error}", "tr": "Geçersiz gaz karışımı: {error}"},
    "series_so_far_header": {"en": "Series so far", "tr": "Şimdiye kadarki seri"},
    "series_entry_bottom_min": {"en": "{minutes:g} min bottom", "tr": "{minutes:g} dk dip"},
    "series_entry_first_no_si": {"en": "First dive — no SI", "tr": "İlk dalış — yüzey aralığı yok"},
    "series_entry_si": {"en": "SI {minutes:g} min", "tr": "Yüzey aralığı {minutes:g} dk"},
    "series_entry_o2": {"en": "O2 {pct:.1f}%", "tr": "O2 %{pct:.1f}"},
    "remove_button": {"en": "Remove", "tr": "Kaldır"},
    "clear_series_button": {"en": "Clear entire series", "tr": "Tüm seriyi temizle"},
    "no_dives_added_info": {
        "en": "No dives added yet. Use the form above to add the first dive.",
        "tr": "Henüz dalış eklenmedi. İlk dalışı eklemek için yukarıdaki formu kullanın.",
    },
    "chained_results_header": {"en": "Chained results", "tr": "Zincirlenmiş sonuçlar"},
    "plan_series_engine_error": {
        "en": (
            "Could not plan this series with the seeded table data: {error}\n\n"
            "Try adjusting depth/time/surface-interval values, or check "
            "**About** for the seeded coverage ranges."
        ),
        "tr": (
            "Bu seri, mevcut tablo verileriyle planlanamadı: {error}\n\n"
            "Derinlik/süre/yüzey aralığı değerlerini ayarlamayı deneyin veya "
            "mevcut kapsam aralıkları için **Hakkında** sayfasına bakın."
        ),
    },
    "dive_expander_title": {
        "en": "Dive #{index} — {gas} @ {depth}, {minutes:g} min bottom time",
        "tr": "Dalış #{index} — {gas} @ {depth}, {minutes:g} dk dip süresi",
    },
    "save_series_header": {"en": "Save this series to a profile", "tr": "Bu seriyi bir profile kaydet"},
    "save_series_need_dive_caption": {
        "en": "Add at least one dive before saving.",
        "tr": "Kaydetmeden önce en az bir dalış ekleyin.",
    },
    "user_label": {"en": "User", "tr": "Kullanıcı"},
    "new_user_option": {"en": "<new user>", "tr": "<yeni kullanıcı>"},
    "new_user_id_label": {"en": "New user id (no slashes)", "tr": "Yeni kullanıcı kimliği (eğik çizgisiz)"},
    "new_user_display_name_label": {"en": "New user display name", "tr": "Yeni kullanıcı görünen adı"},
    "series_label_label": {"en": "Series label", "tr": "Seri etiketi"},
    "series_label_default": {"en": "Series", "tr": "Seri"},
    "save_series_button": {"en": "Save series to profile", "tr": "Seriyi profile kaydet"},
    "user_id_required_error": {
        "en": "A user id is required to save a profile.",
        "tr": "Profil kaydetmek için bir kullanıcı kimliği gereklidir.",
    },
    "series_saved_success": {
        "en": "Saved '{label}' to profile '{user_id}'.",
        "tr": "'{label}' profil '{user_id}' içine kaydedildi.",
    },
    "profile_save_error": {
        "en": "Could not save profile: {error}",
        "tr": "Profil kaydedilemedi: {error}",
    },
    # --- Profiles page ---
    "profiles_page_title": {"en": "Profiles", "tr": "Profiller"},
    "choose_user_header": {"en": "Choose a user", "tr": "Bir kullanıcı seçin"},
    "mode_label": {"en": "Mode", "tr": "Mod"},
    "mode_existing_user": {"en": "Existing user", "tr": "Mevcut kullanıcı"},
    "mode_create_new_user": {"en": "Create new user", "tr": "Yeni kullanıcı oluştur"},
    "no_profiles_info": {
        "en": "No profiles saved yet. Create one, or save a series from Dive Series.",
        "tr": "Henüz kaydedilmiş profil yok. Bir profil oluşturun veya Dalış Serisi'nden bir seri kaydedin.",
    },
    "display_name_label": {"en": "Display name", "tr": "Görünen ad"},
    "create_profile_button": {"en": "Create profile", "tr": "Profil oluştur"},
    "user_id_required_error2": {"en": "A user id is required.", "tr": "Bir kullanıcı kimliği gereklidir."},
    "profile_already_exists_warning": {
        "en": "A profile for '{user_id}' already exists.",
        "tr": "'{user_id}' için bir profil zaten mevcut.",
    },
    "profile_created_success": {
        "en": "Created profile '{user_id}'.",
        "tr": "'{user_id}' profili oluşturuldu.",
    },
    "profile_create_error": {
        "en": "Could not create profile: {error}",
        "tr": "Profil oluşturulamadı: {error}",
    },
    "profile_load_error": {
        "en": "Could not load profile '{user_id}': {error}",
        "tr": "'{user_id}' profili yüklenemedi: {error}",
    },
    "saved_series_header": {"en": "{name}'s saved series", "tr": "{name} adlı kullanıcının kayıtlı serileri"},
    "no_series_saved_info": {
        "en": "No series saved for this user yet. Build one on the Dive Series page.",
        "tr": "Bu kullanıcı için henüz kayıtlı seri yok. Dalış Serisi sayfasında bir tane oluşturun.",
    },
    "series_expander_title": {
        "en": "{label} ({count} dive(s))",
        "tr": "{label} ({count} dalış)",
    },
    "dive_summary_line": {
        "en": "**Dive #{index}** — {gas} @ {depth}, {minutes:g} min bottom time",
        "tr": "**Dalış #{index}** — {gas} @ {depth}, {minutes:g} dk dip süresi",
    },
    "dive_summary_si": {"en": ", SI {minutes:g} min", "tr": ", yüzey aralığı {minutes:g} dk"},
    "dive_summary_first_no_si": {
        "en": " (first dive, no SI)",
        "tr": " (ilk dalış, yüzey aralığı yok)",
    },
    "load_into_series_button": {
        "en": "Load into Dive Series builder",
        "tr": "Dalış Serisi oluşturucusuna yükle",
    },
    "series_loaded_success": {
        "en": "Series loaded. Open **Dive Series** from the sidebar to view/edit it.",
        "tr": "Seri yüklendi. Görüntülemek/düzenlemek için kenar çubuğundan **Dalış Serisi**'ni açın.",
    },
    "load_first_into_plan_button": {
        "en": "Load first dive into Plan Dive",
        "tr": "İlk dalışı Dalış Planla'ya yükle",
    },
    "first_dive_loaded_success": {
        "en": "First dive loaded. Open **Plan Dive** from the sidebar to view it.",
        "tr": "İlk dalış yüklendi. Görüntülemek için kenar çubuğundan **Dalış Planla**'yı açın.",
    },
    # --- About page ---
    "about_page_title": {"en": "About This Tool", "tr": "Bu Araç Hakkında"},
    "about_body": {
        "en": (
            "## What this is\n\n"
            "A **faithful table-lookup calculator** for the **US Navy Diving Manual\n"
            "(Revision 7, Change A, 2018)** decompression tables. It is a table\n"
            "reproduction, not a decompression algorithm — there is no Bühlmann model,\n"
            "no VVAL-18 comparison, and no mid-dive gas-switching engine. Heliox\n"
            "schedules already include their own printed O2 gas switches, so the tool\n"
            "simply displays them.\n\n"
            "## Method notes\n\n"
            "- **Air** — Table 9-7 (no-decompression limits + repetitive group) or\n"
            "  Table 9-9 (decompression schedule + ending group), selected by whether\n"
            "  the (rounded) bottom time exceeds the no-decompression limit at the\n"
            "  (rounded) depth. Depth and bottom time are always rounded **up** to the\n"
            "  next tabulated value, per the manual's rounding rule.\n"
            "- **Nitrox** — handled via the **Equivalent Air Depth (EAD)** method: look\n"
            "  up (or algebraically compute) the EAD from Table 10-1, then run the air\n"
            "  path at that shallower depth. Working ppO2 is capped at **1.4 ata**;\n"
            "  dives beyond that ceiling are flagged and excluded from repetitive\n"
            "  chaining, per the manual.\n"
            "- **Heliox** — Table 12-4 (surface-supplied helium-oxygen), looked up by\n"
            "  depth and bottom time, standalone. There is **no repetitive-group /\n"
            "  residual-nitrogen system for heliox** in the Navy tables — every heliox\n"
            "  result carries a warning that repetitive logic does not apply.\n"
            "- **Repetitive (air/nitrox) dives** — Table 9-8, read in two passes:\n"
            "  prior repetitive group + surface interval → new (credited) group, then\n"
            "  new group + next dive's depth → Residual Nitrogen Time (RNT), added to\n"
            "  the next dive's actual bottom time before its own lookup. Edge cases\n"
            "  (`*` non-repetitive interval, `**` RNT undeterminable, surface intervals\n"
            "  under 10 minutes, nitrox beyond 1.4 ata) are surfaced as warnings rather\n"
            "  than guessed at.\n\n"
            "## Rev 7 note\n\n"
            "Table structure and repetitive-group letters (A–O, plus Z) are unchanged\n"
            "from Rev 6 — only the underlying decompression model changed (Rev 7 uses\n"
            "**VVal-79**, a Thalmann exponential-linear model), which recomputed the\n"
            "numeric limits printed in the tables. This tool reproduces the printed\n"
            "**Rev 7 Change A (2018)** table values, not the model itself.\n\n"
            "## Data provenance — the credibility risk\n\n"
            "**Table data is NOT verified — never use it for real dive planning.**\n"
            "The **air** (9-7/9-8/9-9) and **heliox** (12-4) tables are transcribed\n"
            "from the official US Navy Diving Manual Rev 7 tables PDF, and the\n"
            "**nitrox** (10-1) EAD values are formula-derived from the algebraic\n"
            "Equivalent Air Depth formula. None of this is a full, certified\n"
            "transcription: every table in this build is still marked\n"
            "`verified: false` and is pending a final manual cell-by-cell spot-check.\n"
            "Every dive result on this site surfaces that as a visible warning —\n"
            "verify every value against a physical manual before any real use.\n\n"
            "## Table sources\n\n"
            "- Rev 7 tables — https://www.divetable.info/workshop/USN_Rev7_Tables.pdf\n"
            "- Rev 6 tables (for comparison) — https://www.divetable.info/workshop/USN_Rev6.pdf\n"
            "- Full manual (NAVSEA) — https://www.navsea.navy.mil/Portals/103/Documents/SUPSALV/Diving/US%20DIVING%20MANUAL_REV7.pdf\n"
            "- UHMS Table 2A-1 (clean cell reference) — https://www.uhms.org/images/MEDFAQs/February-2017/2nd/US_DIVING_MANUALREV7_TT2A.pdf\n"
            "- VVal-79 validation — https://pmc.ncbi.nlm.nih.gov/articles/PMC7276270/\n"
            "- EAD / MOD formulas — https://en.wikipedia.org/wiki/Equivalent_air_depth ,\n"
            "  https://en.wikipedia.org/wiki/Maximum_operating_depth\n"
            "- fsw/msw units — https://en.wikipedia.org/wiki/Metre_sea_water\n\n"
            "See `docs/research/usn-rev7-reference.md` in the project repository for\n"
            "the full research reference this tool was built against."
        ),
        "tr": (
            "## Bu nedir\n\n"
            "**US Navy Diving Manual (Revizyon 7, Değişiklik A, 2018)** "
            "dekompresyon tabloları için **sadık bir tablo sorgulama hesaplayıcısı**. "
            "Bu bir tablo yeniden üretimidir, bir dekompresyon algoritması değildir "
            "— Bühlmann modeli, VVAL-18 karşılaştırması veya dalış-içi gaz geçiş "
            "motoru yoktur. Helioks çizelgeleri, kendi basılı O2 gaz geçişlerini "
            "zaten içerir; araç bunları sadece görüntüler.\n\n"
            "## Yöntem notları\n\n"
            "- **Hava** — dip süresinin (yuvarlanmış) o derinlikteki (yuvarlanmış) "
            "dekompresyonsuz sınırı aşıp aşmadığına göre Tablo 9-7 (dekompresyonsuz "
            "sınırlar + tekrar grubu) veya Tablo 9-9 (dekompresyon çizelgesi + bitiş "
            "grubu) seçilir. Derinlik ve dip süresi, kılavuzun yuvarlama kuralına "
            "göre her zaman bir sonraki tablo değerine **yukarı** yuvarlanır.\n"
            "- **Nitroks** — **Eşdeğer Hava Derinliği (EAD)** yöntemiyle işlenir: "
            "Tablo 10-1'den EAD aranır (veya cebirsel olarak hesaplanır), ardından "
            "hava yolu bu daha sığ derinlikte çalıştırılır. Çalışma ppO2'si **1.4 "
            "ata** ile sınırlıdır; bu sınırı aşan dalışlar işaretlenir ve kılavuza "
            "göre tekrarlı zincirlemeden hariç tutulur.\n"
            "- **Helioks** — Tablo 12-4 (yüzeyden beslemeli helyum-oksijen), "
            "derinlik ve dip süresine göre bağımsız olarak aranır. Donanma "
            "tablolarında **helioks için tekrar grubu / artık azot sistemi "
            "yoktur** — her helioks sonucu, tekrar mantığının geçerli olmadığına "
            "dair bir uyarı taşır.\n"
            "- **Tekrarlı (hava/nitroks) dalışlar** — Tablo 9-8, iki geçişte "
            "okunur: önceki tekrar grubu + yüzey aralığı → yeni (kredilendirilmiş) "
            "grup, ardından yeni grup + sonraki dalışın derinliği → Artık Azot "
            "Süresi (RNT), sonraki dalışın gerçek dip süresine kendi sorgusundan "
            "önce eklenir. Uç durumlar (`*` tekrarlı olmayan aralık, `**` RNT "
            "belirlenemez, 10 dakikanın altındaki yüzey aralıkları, 1.4 ata üzeri "
            "nitroks) tahmin edilmek yerine uyarı olarak sunulur.\n\n"
            "## Rev 7 notu\n\n"
            "Tablo yapısı ve tekrar grubu harfleri (A–O, artı Z) Rev 6'dan "
            "değişmemiştir — yalnızca altta yatan dekompresyon modeli değişmiştir "
            "(Rev 7, bir Thalmann üstel-doğrusal modeli olan **VVal-79**'u "
            "kullanır), bu da tablolarda basılı sayısal sınırların yeniden "
            "hesaplanmasına yol açmıştır. Bu araç, modelin kendisini değil, basılı "
            "**Rev 7 Değişiklik A (2018)** tablo değerlerini yeniden üretir.\n\n"
            "## Veri kökeni — güvenilirlik riski\n\n"
            "**Tablo verileri doğrulanmamıştır — gerçek dalış planlamasında asla "
            "kullanmayın.** **Hava** (9-7/9-8/9-9) ve **helioks** (12-4) tabloları "
            "resmi US Navy Diving Manual Rev 7 tablolar PDF'inden aktarılmıştır ve "
            "**nitroks** (10-1) EAD değerleri, cebirsel Eşdeğer Hava Derinliği "
            "formülünden türetilmiştir. Bunların hiçbiri tam, onaylı bir "
            "aktarım değildir: bu yapıdaki her tablo hâlâ `verified: false` olarak "
            "işaretlidir ve kılavuzla hücre hücre nihai bir kontrol beklemektedir. "
            "Bu sitedeki her dalış sonucu bunu görünür bir uyarı olarak sunar — "
            "gerçek kullanımdan önce her değeri fiziksel bir kılavuzla doğrulayın.\n\n"
            "## Tablo kaynakları\n\n"
            "- Rev 7 tabloları — https://www.divetable.info/workshop/USN_Rev7_Tables.pdf\n"
            "- Rev 6 tabloları (karşılaştırma için) — https://www.divetable.info/workshop/USN_Rev6.pdf\n"
            "- Tam kılavuz (NAVSEA) — https://www.navsea.navy.mil/Portals/103/Documents/SUPSALV/Diving/US%20DIVING%20MANUAL_REV7.pdf\n"
            "- UHMS Tablo 2A-1 (temiz hücre referansı) — https://www.uhms.org/images/MEDFAQs/February-2017/2nd/US_DIVING_MANUALREV7_TT2A.pdf\n"
            "- VVal-79 doğrulaması — https://pmc.ncbi.nlm.nih.gov/articles/PMC7276270/\n"
            "- EAD / MOD formülleri — https://en.wikipedia.org/wiki/Equivalent_air_depth ,\n"
            "  https://en.wikipedia.org/wiki/Maximum_operating_depth\n"
            "- fsw/msw birimleri — https://en.wikipedia.org/wiki/Metre_sea_water\n\n"
            "Bu aracın dayandığı tüm araştırma referansı için proje deposundaki "
            "`docs/research/usn-rev7-reference.md` dosyasına bakın."
        ),
    },
    # --- Engine warnings (best-effort, pattern-matched) ---
    "warn_repetitive_na": {
        "en": (
            "Heliox has no repetitive-group / residual-nitrogen system in the Navy "
            "tables; repetitive logic is not applicable to this dive."
        ),
        "tr": (
            "Donanma tablolarında helioks için tekrar grubu / artık azot sistemi "
            "yoktur; tekrar mantığı bu dalış için geçerli değildir."
        ),
    },
    "warn_exceptional_exposure": {
        "en": "Exceptional exposure schedule — see manual cautions",
        "tr": "Olağanüstü maruziyet çizelgesi — kılavuzdaki uyarılara bakın",
    },
    "warn_depth_rounded": {
        "en": "Depth rounded up from {from_depth} to {to_depth} fsw per table rules",
        "tr": "Derinlik, tablo kurallarına göre {from_depth} fsw'den {to_depth} fsw'ye yukarı yuvarlandı",
    },
    "warn_bottom_time_exceeds_ndl": {
        "en": (
            "Bottom time {bottom_time} min exceeds NDL of {ndl} min at "
            "{depth} fsw; decompression required (Table 9-9)"
        ),
        "tr": (
            "Dip süresi {bottom_time} dk, {depth} fsw'deki {ndl} dk'lık NDL'yi "
            "aşıyor; dekompresyon gerekli (Tablo 9-9)"
        ),
    },
    "warn_ppo2_exceeds": {
        "en": (
            "ppO2 at {depth} fsw is {ppo2} ata, exceeding the "
            "{ceiling} ata working limit — requires CO authorization "
            "and surface-supplied gear; repetitive dives are NOT authorized."
        ),
        "tr": (
            "{depth} fsw'deki ppO2 değeri {ppo2} ata olup, {ceiling} ata'lık "
            "çalışma sınırını aşıyor — CO (Dalış Subayı) yetkisi ve yüzeyden "
            "beslemeli ekipman gerektirir; tekrarlı dalışlara İZİN VERİLMEZ."
        ),
    },
    "warn_mod_exceeded": {
        "en": (
            "Requested depth {depth} fsw exceeds MOD of {mod} fsw "
            "for FO2={fo2} at ppO2_max={ceiling} ata"
        ),
        "tr": (
            "İstenen {depth} fsw derinliği, FO2={fo2} ve ppO2_maks={ceiling} ata "
            "için {mod} fsw olan MOD (Maksimum Operasyon Derinliği) değerini aşıyor"
        ),
    },
    "warn_ead_fallback": {
        "en": (
            "EAD for {depth} fsw / FO2={fo2} not in the seeded Table "
            "10-1 subset; computed via the algebraic EAD formula instead"
        ),
        "tr": (
            "{depth} fsw / FO2={fo2} için EAD, mevcut Tablo 10-1 alt "
            "kümesinde yok; bunun yerine cebirsel EAD formülüyle hesaplandı"
        ),
    },
    "warn_heliox_o2_window": {
        "en": (
            "Requested FO2={fo2} is outside the Table 12-4 window for "
            "{depth} fsw (Max {max_o2}% / Min {min_o2}%)"
        ),
        "tr": (
            "İstenen FO2={fo2}, {depth} fsw için Tablo 12-4 penceresinin dışında "
            "(Maks %{max_o2} / Min %{min_o2})"
        ),
    },
    "warn_table_unverified": {
        "en": "Table {table} data not yet verified against the manual",
        "tr": "Tablo {table} verileri henüz kılavuza karşı doğrulanmadı",
    },
    "warn_surface_interval_below_floor": {
        "en": (
            "Surface interval {si} min is below the "
            "{floor}-minute credit floor; tables do not credit "
            "intervals this short — treating as a continuation dive "
            "(no RNT computed)."
        ),
        "tr": (
            "Yüzey aralığı {si} dk, {floor} dakikalık kredi eşiğinin altında; "
            "tablolar bu kadar kısa aralıkları kredilendirmez — devam dalışı "
            "olarak ele alınıyor (RNT hesaplanmadı)."
        ),
    },
    "warn_non_repetitive_interval": {
        "en": (
            "Surface interval {si} min exceeds the "
            "non-repetitive threshold for group {group}; the "
            "next dive is not a repetitive dive (no RNT added)."
        ),
        "tr": (
            "Yüzey aralığı {si} dk, {group} grubu için tekrarlı olmama eşiğini "
            "aşıyor; sonraki dalış tekrarlı bir dalış değildir (RNT eklenmedi)."
        ),
    },
    "warn_rnt_undeterminable": {
        "en": (
            "RNT undeterminable for group {group} at {depth} fsw "
            "(manual para 9-9.1 subpara 8, substitute-depth rule) — verify "
            "exact procedure against the manual before implementing; no RNT "
            "value fabricated."
        ),
        "tr": (
            "{group} grubu için {depth} fsw'de RNT belirlenemiyor (kılavuz "
            "madde 9-9.1 alt madde 8, yerine derinlik kuralı) — uygulamadan "
            "önce tam prosedürü kılavuzla doğrulayın; hiçbir RNT değeri "
            "uydurulmadı."
        ),
    },
}


def render_language_toggle(container) -> str:
    """Render the EN/TR language selector in the given container.

    Stores the choice in ``st.session_state["lang"]`` (default "en") so
    it persists across pages, exactly like the units toggle. Must be
    called before any ``t()`` lookups that should reflect a change made
    on this run.
    """
    st.session_state.setdefault(LANG_KEY, DEFAULT_LANG)
    codes = list(LANGUAGES.keys())
    choice = container.radio(
        t("language_label"),
        options=codes,
        format_func=lambda code: LANGUAGES.get(code, code),
        horizontal=True,
        key=LANG_KEY,
    )
    return choice


def t(key: str, **kwargs) -> str:
    """Look up ``key`` in the active language, formatting with kwargs.

    Falls back to English if the key or language is missing, and to the
    raw key itself if even English is missing — this must never crash a
    page, so any formatting error also falls back to the unformatted
    string rather than raising.
    """
    lang = st.session_state.get(LANG_KEY, DEFAULT_LANG)
    entry = TRANSLATIONS.get(key)
    if entry is None:
        return key
    text = entry.get(lang) or entry.get(DEFAULT_LANG) or key
    if not kwargs:
        return text
    try:
        return text.format(**kwargs)
    except (KeyError, IndexError, ValueError):
        return text
