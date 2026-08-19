import urllib.request
import urllib.parse
import json
import logging
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QHBoxLayout, QPushButton
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPoint, QTimer, QRect, QLocale
from PyQt6.QtGui import QFont, QPalette, QColor, QPainter, QPen, QCursor
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from icon_manager import load_icon
from translator import tr

class TranslationWorker(QThread):
    finished = pyqtSignal(str, dict)  # (original, translation_details)
    error = pyqtSignal(str)

    def __init__(self, text, target_lang="en", dict_source="free_dict"):
        super().__init__()
        self.text = text
        self.target_lang = target_lang
        self.dict_source = dict_source

    def run(self):
        try:
            cleaned = self.text.strip()
            if not cleaned:
                self.finished.emit(self.text, {"translation": ""})
                return

            if self.dict_source == "free_dict":
                self._fetch_free_dictionary(cleaned)
            elif self.dict_source == "both":
                self._fetch_both(cleaned)
            else:
                self._fetch_google_translate(cleaned)
        except Exception as e:
            logging.error(f"Translation error: {e}")
            self.error.emit(str(e))

    def _get_free_dictionary_dict(self, cleaned):
        import re
        word_cleaned = re.sub(r'^[^\w]+|[^\w]+$', '', cleaned)
        if not word_cleaned:
            word_cleaned = cleaned

        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{urllib.parse.quote(word_cleaned)}"
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        import ssl
        context = ssl._create_unverified_context()

        try:
            with urllib.request.urlopen(req, timeout=5, context=context) as response:
                data = json.loads(response.read().decode('utf-8'))
                if data and isinstance(data, list) and len(data) > 0:
                    entry = data[0]
                    word = entry.get("word", word_cleaned)
                    
                    phonetic = entry.get("phonetic", "")
                    phonetics = entry.get("phonetics", [])
                    audio_url = ""
                    if not phonetic:
                        for ph in phonetics:
                            if ph.get("text"):
                                phonetic = ph.get("text")
                                break
                    for ph in phonetics:
                        if ph.get("audio"):
                            audio_url = ph.get("audio")
                            break

                    meanings = entry.get("meanings", [])
                    parts_of_speech = {}
                    synonyms = {}
                    main_def = ""

                    for m in meanings:
                        pos = m.get("partOfSpeech", "general")
                        defs = m.get("definitions", [])
                        pos_defs = []
                        for d in defs:
                            def_text = d.get("definition", "")
                            example = d.get("example", "")
                            if def_text:
                                pos_defs.append({"definition": def_text, "example": example})
                                if not main_def:
                                    main_def = def_text
                        if pos_defs:
                            parts_of_speech[pos] = pos_defs
                        
                        syn_list = m.get("synonyms", [])
                        if syn_list:
                            synonyms[pos] = syn_list

                    if parts_of_speech:
                        return {
                            "is_free_dict": True,
                            "word": word,
                            "phonetic": phonetic,
                            "audio_url": audio_url,
                            "translation": main_def or word,
                            "parts_of_speech": parts_of_speech,
                            "synonyms": synonyms
                        }
        except Exception as e:
            logging.info(f"Free Dictionary lookup notice for '{cleaned}': {e}")
        return None

    def _get_google_translate_dict(self, cleaned, target_lang):
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={target_lang}&dt=t&dt=bd&dt=ss&q={urllib.parse.quote(cleaned)}"
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        import ssl
        context = ssl._create_unverified_context()
        try:
            with urllib.request.urlopen(req, timeout=5, context=context) as response:
                data = json.loads(response.read().decode('utf-8'))
                if data and data[0]:
                    translated = "".join([part[0] for part in data[0] if part[0]])
                    
                    parts_of_speech = {}
                    if len(data) > 1 and data[1]:
                        for entry in data[1]:
                            if len(entry) >= 2:
                                pos = entry[0]
                                words = entry[1]
                                if pos and words:
                                    parts_of_speech[pos] = words
                                    
                    synonyms = {}
                    if len(data) > 11 and data[11]:
                        for entry in data[11]:
                            if len(entry) >= 2:
                                pos = entry[0]
                                syn_list = []
                                for item in entry[1]:
                                    if item and isinstance(item, list) and len(item) > 0:
                                        syn_list.extend(item[0])
                                if pos and syn_list:
                                    synonyms[pos] = syn_list

                    return {
                        "translation": translated,
                        "parts_of_speech": parts_of_speech,
                        "synonyms": synonyms
                    }
        except Exception as e:
            logging.error(f"Google Translate lookup error for '{cleaned}': {e}")
        return None

    def _fetch_free_dictionary(self, cleaned):
        res = self._get_free_dictionary_dict(cleaned)
        if res:
            self.finished.emit(cleaned, res)
            return
        res_gt = self._get_google_translate_dict(cleaned, "en")
        if res_gt:
            res_gt["fallback_notice"] = "Google Translate"
            self.finished.emit(cleaned, res_gt)
        else:
            self.error.emit("Word not found in dictionary or translator")

    def _fetch_google_translate(self, cleaned):
        res_gt = self._get_google_translate_dict(cleaned, self.target_lang)
        if res_gt:
            self.finished.emit(cleaned, res_gt)
        else:
            self.error.emit("Empty response from translation API")

    def _fetch_both(self, cleaned):
        free_res = self._get_free_dictionary_dict(cleaned)
        gt_res = self._get_google_translate_dict(cleaned, self.target_lang)

        if free_res and gt_res:
            combined = {
                "is_both": True,
                "is_free_dict": True,
                "word": free_res.get("word", cleaned),
                "phonetic": free_res.get("phonetic", ""),
                "audio_url": free_res.get("audio_url", ""),
                "parts_of_speech": free_res.get("parts_of_speech", {}),
                "synonyms": free_res.get("synonyms", {}),
                "gt_translation": gt_res.get("translation", ""),
                "gt_parts_of_speech": gt_res.get("parts_of_speech", {}),
                "gt_synonyms": gt_res.get("synonyms", {}),
                "translation": f"{free_res.get('translation', '')} / {gt_res.get('translation', '')}"
            }
            self.finished.emit(cleaned, combined)
        elif free_res:
            self.finished.emit(cleaned, free_res)
        elif gt_res:
            self.finished.emit(cleaned, gt_res)
        else:
            self.error.emit("Failed to fetch dictionary or translation")


class TranslationPopup(QFrame):
    mouseLeft = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.setObjectName("translationPopup")
        
        self.media_player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.media_player.setAudioOutput(self.audio_output)
        
        self._memory_cache = {}
        self._current_audio_url = ""
        self.active_workers = []
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        self.original_label = QLabel()
        self.original_label.setObjectName("translationOriginalLabel")
        self.original_label.setStyleSheet("font-weight: bold; font-size: 13pt; color: #FFFFFF;")
        header_layout.addWidget(self.original_label)
        
        header_layout.addStretch()
        
        self.pronounce_btn = QPushButton()
        self.pronounce_btn.setObjectName("pronounceBtn")
        self.pronounce_btn.setIcon(load_icon("volume_hight"))
        self.pronounce_btn.setFixedSize(24, 24)
        self.pronounce_btn.setToolTip(tr("translator.listen_pronunciation"))
        self.pronounce_btn.clicked.connect(self._play_pronunciation)
        self.pronounce_btn.hide()
        header_layout.addWidget(self.pronounce_btn)
        
        self.dict_btn = QPushButton()
        self.dict_btn.setObjectName("addToDictBtn")
        self.dict_btn.setIcon(load_icon("add"))
        self.dict_btn.setFixedSize(24, 24)
        self.dict_btn.setToolTip(tr("translator.add_to_dictionary"))
        self.dict_btn.clicked.connect(self._add_to_dictionary)
        self.dict_btn.hide()
        header_layout.addWidget(self.dict_btn)
        
        layout.addLayout(header_layout)
        
        self.translation_label = QLabel()
        self.translation_label.setObjectName("translationResultLabel")
        self.translation_label.setWordWrap(True)
        self.translation_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.translation_label)
        
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor("#444444"))
        painter.setPen(QPen(QColor("#808080"), 1))
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 8.0, 8.0)

    def _get_db(self):
        parent = self.parent()
        if parent and hasattr(parent, "db") and parent.db:
            return parent.db
        if parent and hasattr(parent, "player_window") and parent.player_window and hasattr(parent.player_window, "db"):
            return parent.player_window.db
        return None

    def show_translation(self, text, target_lang="en", anchor_pos=QPoint(), dict_source="free_dict"):
        cleaned = text.strip()
        if not cleaned:
            self.hide()
            return

        self.last_anchor_pos = anchor_pos
        db_target_lang = f"{dict_source}:{target_lang}"
        cache_key = (cleaned, db_target_lang)

        if cache_key in self._memory_cache:
            logging.info(f"Translation cache hit (L1 memory) for: '{cleaned}' -> '{db_target_lang}'")
            self.original_label.setText(text)
            self.show()
            self.raise_()
            self._on_translation_success(text, self._memory_cache[cache_key])
            return

        db = self._get_db()
        if db:
            cached_result = db.get_cached_translation(cleaned, db_target_lang)
            if cached_result:
                logging.info(f"Translation cache hit (L2 database) for: '{cleaned}' -> '{db_target_lang}'")
                self._memory_cache[cache_key] = cached_result
                self.original_label.setText(text)
                self.show()
                self.raise_()
                self._on_translation_success(text, cached_result)
                return

        self.original_label.setText(text)
        self.translation_label.setText("...")
        self.dict_btn.hide()
        self.pronounce_btn.hide()
        self.adjustSize()
        self.position_popup(anchor_pos)
        self.show()
        self.raise_()

        worker = TranslationWorker(text, target_lang, dict_source=dict_source)
        
        def on_success(orig, trans, w=worker):
            try:
                self.active_workers.remove(w)
            except ValueError:
                pass
            self._memory_cache[cache_key] = trans
            db_inst = self._get_db()
            if db_inst:
                db_inst.save_cached_translation(cleaned, db_target_lang, trans)
            self._on_translation_success(orig, trans)
            
        def on_error(err, w=worker):
            try:
                self.active_workers.remove(w)
            except ValueError:
                pass
            self.translation_label.setText(f"Error: {err}")

        worker.finished.connect(on_success)
        worker.error.connect(on_error)
        self.active_workers.append(worker)
        worker.start()

    def _on_translation_success(self, original, result_dict):
        is_both = result_dict.get("is_both", False)
        is_free_dict = result_dict.get("is_free_dict", False)
        translation = result_dict.get("translation", "")
        parts_of_speech = result_dict.get("parts_of_speech", {})
        synonyms = result_dict.get("synonyms", {})
        
        html = ""
        if is_both:
            word = result_dict.get("word", original)
            phonetic = result_dict.get("phonetic", "")
            
            html += f"<div style='margin-bottom: 4px;'><span style='color: #4ECCA3; font-size: 10pt; font-weight: bold;'>{phonetic}</span>" if phonetic else "<div>"
            html += f" <span style='color: #808080; font-size: 8pt;'>(Free Dictionary)</span></div>"
            
            pos_lines = []
            for pos_name, def_items in parts_of_speech.items():
                from translator import tr
                translated_pos = tr(f"translator.{pos_name}")
                if translated_pos == f"translator.{pos_name}":
                    translated_pos = pos_name.capitalize()
                
                def_html_parts = []
                if isinstance(def_items, list):
                    for idx, item in enumerate(def_items[:2], 1):
                        if isinstance(item, dict):
                            d_text = item.get("definition", "")
                            ex_text = item.get("example", "")
                            line = f"<div style='color: #eaeaea;'>{idx}. {d_text}</div>"
                            if ex_text:
                                line += f"<div style='color: #a0a0a0; font-style: italic; margin-left: 10px;'>“{ex_text}”</div>"
                            def_html_parts.append(line)
                        else:
                            def_html_parts.append(f"<div style='color: #eaeaea;'>• {item}</div>")
                
                pos_lines.append(
                    f"<tr><td style='color: #018574; font-weight: bold; padding-right: 8px; vertical-align: top;'>{translated_pos}:</td><td style='color: #eaeaea;'>{''.join(def_html_parts)}</td></tr>"
                )
                
            if pos_lines:
                html += f"<table style='margin-top: 4px; margin-bottom: 4px; font-size: 9.5pt;'>{''.join(pos_lines)}</table>"

            gt_trans = result_dict.get("gt_translation", "")
            gt_pos = result_dict.get("gt_parts_of_speech", {})
            if gt_trans or gt_pos:
                html += f"<hr style='border: 0; border-top: 1px solid #555555; margin: 6px 0;'/>"
                if gt_trans:
                    html += f"<div style='color: #FFD700; font-weight: bold; margin-bottom: 4px;'>{gt_trans} <span style='color: #808080; font-size: 8pt;'>(Google Translate)</span></div>"
                
                gt_pos_lines = []
                for pos_name, words in gt_pos.items():
                    from translator import tr
                    translated_pos = tr(f"translator.{pos_name}")
                    if translated_pos == f"translator.{pos_name}":
                        translated_pos = pos_name.capitalize()
                    
                    word_list_str = ", ".join(words[:5]) if isinstance(words, list) else str(words)
                    gt_pos_lines.append(
                        f"<tr><td style='color: #808080; font-weight: bold; padding-right: 8px; vertical-align: top;'>{translated_pos}:</td><td style='color: #eaeaea;'>{word_list_str}</td></tr>"
                    )
                    
                if gt_pos_lines:
                    html += f"<table style='margin-top: 4px; margin-bottom: 4px; font-size: 9.5pt;'>{''.join(gt_pos_lines)}</table>"

        elif is_free_dict:
            word = result_dict.get("word", original)
            phonetic = result_dict.get("phonetic", "")
            
            html += f"<div style='margin-bottom: 4px;'><span style='color: #4ECCA3; font-size: 10pt; font-weight: bold;'>{phonetic}</span>" if phonetic else "<div>"
            html += f" <span style='color: #808080; font-size: 8pt;'>(Free Dictionary)</span></div>"
            
            pos_lines = []
            for pos_name, def_items in parts_of_speech.items():
                from translator import tr
                translated_pos = tr(f"translator.{pos_name}")
                if translated_pos == f"translator.{pos_name}":
                    translated_pos = pos_name.capitalize()
                
                def_html_parts = []
                if isinstance(def_items, list):
                    for idx, item in enumerate(def_items[:2], 1):
                        if isinstance(item, dict):
                            d_text = item.get("definition", "")
                            ex_text = item.get("example", "")
                            line = f"<div style='color: #eaeaea;'>{idx}. {d_text}</div>"
                            if ex_text:
                                line += f"<div style='color: #a0a0a0; font-style: italic; margin-left: 10px;'>“{ex_text}”</div>"
                            def_html_parts.append(line)
                        else:
                            def_html_parts.append(f"<div style='color: #eaeaea;'>• {item}</div>")
                
                pos_lines.append(
                    f"<tr><td style='color: #018574; font-weight: bold; padding-right: 8px; vertical-align: top;'>{translated_pos}:</td><td style='color: #eaeaea;'>{''.join(def_html_parts)}</td></tr>"
                )
                
            if pos_lines:
                html += f"<table style='margin-top: 4px; margin-bottom: 4px; font-size: 9.5pt;'>{''.join(pos_lines)}</table>"
                
            all_synonyms = []
            for pos_name, syn_list in synonyms.items():
                if isinstance(syn_list, list):
                    all_synonyms.extend(syn_list)
            seen = set()
            unique_synonyms = [x for x in all_synonyms if not (x in seen or seen.add(x))]
            if unique_synonyms:
                from translator import tr
                label_synonyms = tr("translator.synonyms")
                if label_synonyms == "translator.synonyms":
                    label_synonyms = "Synonyms"
                syn_str = ", ".join(unique_synonyms[:8])
                if pos_lines:
                    html += f"<hr style='border: 0; border-top: 1px solid #555555; margin: 4px 0;'/>"
                html += f"<div style='font-size: 9pt; color: #a0a0a0; margin-top: 4px;'><b style='color: #808080;'>{label_synonyms}:</b> {syn_str}</div>"

        else:
            # Standard Google Translate layout
            fallback_notice = result_dict.get("fallback_notice", "")
            badge = f" <span style='color: #808080; font-size: 8pt;'>({fallback_notice})</span>" if fallback_notice else ""
            html = f"<div style='color: #FFD700;'>{translation}{badge}</div>"
            
            pos_lines = []
            for pos_name, words in parts_of_speech.items():
                from translator import tr
                translated_pos = tr(f"translator.{pos_name}")
                if translated_pos == f"translator.{pos_name}":
                    translated_pos = pos_name.capitalize()
                
                word_list_str = ", ".join(words[:5]) if isinstance(words, list) else str(words)
                pos_lines.append(
                    f"<tr><td style='color: #808080; font-weight: bold; padding-right: 8px; vertical-align: top;'>{translated_pos}:</td><td style='color: #eaeaea;'>{word_list_str}</td></tr>"
                )
                
            if pos_lines:
                html += f"<table style='margin-top: 6px; margin-bottom: 6px; font-size: 10pt;'>{''.join(pos_lines)}</table>"
                
            all_synonyms = []
            for pos_name, syn_list in synonyms.items():
                if isinstance(syn_list, list):
                    all_synonyms.extend(syn_list)
                
            seen = set()
            unique_synonyms = [x for x in all_synonyms if not (x in seen or seen.add(x))]
            
            if unique_synonyms:
                from translator import tr
                label_synonyms = tr("translator.synonyms")
                if label_synonyms == "translator.synonyms":
                    label_synonyms = "Synonyms"
                syn_str = ", ".join(unique_synonyms[:8])
                
                if pos_lines:
                    html += f"<hr style='border: 0; border-top: 1px solid #555555; margin: 4px 0;'/>"
                html += f"<div style='font-size: 9pt; color: #a0a0a0; margin-top: 4px;'><b style='color: #808080;'>{label_synonyms}:</b> {syn_str}</div>"

        self.translation_label.setText(html)
        
        audio_url = result_dict.get("audio_url", "")
        self._current_audio_url = audio_url
        if audio_url:
            self.pronounce_btn.show()
        else:
            self.pronounce_btn.hide()
            
        self.dict_btn.show()
        self.current_original = original.strip()
        self.current_translation = translation.strip()
        
        db = self._get_db()
        is_added = False
        if db and self.current_original:
            is_added = db.is_in_dictionary(self.current_original)
            
        from translator import tr
        if is_added:
            self.dict_btn.setIcon(load_icon("check"))
            self.dict_btn.setToolTip(tr("translator.already_in_dictionary"))
            self.dict_btn.setProperty("added", "true")
        else:
            self.dict_btn.setIcon(load_icon("add"))
            self.dict_btn.setToolTip(tr("translator.add_to_dictionary"))
            self.dict_btn.setProperty("added", "false")
            
        self.dict_btn.style().unpolish(self.dict_btn)
        self.dict_btn.style().polish(self.dict_btn)
        self.dict_btn.show()

        from translator import tr
        tooltip_pronounce = tr("translator.listen_pronunciation")
        if tooltip_pronounce == "translator.listen_pronunciation":
            tooltip_pronounce = "Listen pronunciation"
        self.pronounce_btn.setIcon(load_icon("volume_hight"))
        self.pronounce_btn.setToolTip(tooltip_pronounce)
        self.pronounce_btn.show()

        self.adjustSize()
        if hasattr(self, "last_anchor_pos") and self.last_anchor_pos:
            self.position_popup(self.last_anchor_pos)
        self.raise_()

    def _on_translation_error(self, err_msg):
        self.translation_label.setText("Translation failed")
        self.current_original = None
        self.current_translation = None
        self.dict_btn.hide()
        self.pronounce_btn.hide()
        self.adjustSize()
        if hasattr(self, "last_anchor_pos") and self.last_anchor_pos:
            self.position_popup(self.last_anchor_pos)
        self.raise_()

    def _on_dict_btn_clicked(self):
        db = self._get_db()
        if not db or not self.current_original:
            return
        
        is_added = db.is_in_dictionary(self.current_original)
        from translator import tr
        if is_added:
            db.remove_from_dictionary(self.current_original)
            self.dict_btn.setIcon(load_icon("add"))
            self.dict_btn.setToolTip(tr("translator.add_to_dictionary"))
            self.dict_btn.setProperty("added", "false")
        else:
            db.add_to_dictionary(self.current_original, self.current_translation)
            self.dict_btn.setIcon(load_icon("check"))
            self.dict_btn.setToolTip(tr("translator.already_in_dictionary"))
            self.dict_btn.setProperty("added", "true")
            
        self.dict_btn.style().unpolish(self.dict_btn)
        self.dict_btn.style().polish(self.dict_btn)
        self.dict_btn.update()
        
        self.adjustSize()
        if hasattr(self, "last_anchor_pos") and self.last_anchor_pos:
            self.position_popup(self.last_anchor_pos)

    def _on_pronounce_btn_clicked(self):
        if not self.current_original:
            return
        
        if not hasattr(self, "tts"):
            try:
                from PyQt6.QtTextToSpeech import QTextToSpeech
                self.tts = QTextToSpeech(self)
            except Exception as e:
                logging.error(f"Failed to initialize QTextToSpeech: {e}")
                self.tts = None
                
        if self.tts:
            try:
                self.tts.stop()
                
                # Check characters to determine locale (defaulting to English if Latin, Russian if Cyrillic)
                import re
                if re.search(r'[\u0400-\u04FF]', self.current_original):
                    from PyQt6.QtCore import QLocale
                    self.tts.setLocale(QLocale("ru_RU"))
                else:
                    from PyQt6.QtCore import QLocale
                    self.tts.setLocale(QLocale("en_US"))
                    
                self.tts.say(self.current_original)
            except Exception as e:
                logging.error(f"Error during speech synthesis: {e}")

    def _play_pronunciation(self):
        if self._current_audio_url:
            try:
                from PyQt6.QtCore import QUrl
                self.media_player.setSource(QUrl(self._current_audio_url))
                self.media_player.play()
                return
            except Exception as e:
                logging.error(f"Error playing audio pronunciation: {e}")
        self._on_pronounce_btn_clicked()

    def _add_to_dictionary(self):
        self._on_dict_btn_clicked()

    def position_popup(self, anchor_pos):
        """Move the popup to be centered horizontally above the anchor point."""
        self.adjustSize()
        w = self.width()
        h = self.height()
        
        # Determine current screen based on anchor point
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.screenAt(anchor_pos)
        if not screen:
            screen = QApplication.primaryScreen()
            
        screen_geo = screen.availableGeometry()

        target_x = anchor_pos.x() - w // 2
        # Align bottom of popup near the top of the word/phrase (with a tiny 4px safety gap)
        target_y = anchor_pos.y() - h - 4

        # Clamp inside screen boundary
        margin = 15
        target_x = max(screen_geo.left() + margin, min(target_x, screen_geo.right() - w - margin))
        target_y = max(screen_geo.top() + margin, min(target_y, screen_geo.bottom() - h - margin))

        self.move(target_x, target_y)

    def leaveEvent(self, event):
        from PyQt6.QtGui import QCursor
        # Only handle leave event if mouse is actually outside the popup geometry
        if not self.rect().contains(self.mapFromGlobal(QCursor.pos())):
            self.hide()
            self.mouseLeft.emit()
        super().leaveEvent(event)

    def enterEvent(self, event):
        self.hide_timer.stop()
        super().enterEvent(event)

    def hideEvent(self, event):
        super().hideEvent(event)
        parent = self.parent()
        if parent and hasattr(parent, "_apply_secondary_visibility"):
            parent._apply_secondary_visibility()
