from cat.mad_hatter.decorators import hook, plugin
from cat.log import log
import json
import os
import re
from datetime import datetime
from typing import Optional, Dict, Any

# Configurazione plugin
PLUGIN_SETTINGS = {
    "max_notes": 100,
    "max_note_length": 200,
    "max_history_chars": 2000,
    "relevance_threshold": 0.7,
    "cleanup_interval_days": 30
}

class ContextualTagsManager:
    def __init__(self):
        self.notes_dir = "contextual_notes"
        self.ensure_notes_directory()
        self.tag_cache = {}
    
    def ensure_notes_directory(self):
        """Crea la directory per le note se non esiste"""
        try:
            os.makedirs(self.notes_dir, exist_ok=True)
            log.info(f"Directory note inizializzata: {self.notes_dir}")
        except Exception as e:
            log.error(f"Errore creazione directory note: {e}")
    
    def sanitize_tag(self, tag: str) -> str:
        """Sanitizza il tag per uso come nome file"""
        if not tag:
            return "general"
        
        # Rimuove caratteri non sicuri per filename
        sanitized = re.sub(r'[^\w\-_\s]', '', tag.lower())
        sanitized = re.sub(r'\s+', '_', sanitized.strip())
        
        # Limita lunghezza
        return sanitized[:30] if sanitized else "general"
    
    def extract_tag_from_conversation(self, cat, conversation_history: str) -> str:
        """Estrae tag principale dalla conversazione"""
        try:
            # Limita la lunghezza della cronologia
            limited_history = conversation_history[-PLUGIN_SETTINGS["max_history_chars"]:]
            
            prompt = (
                "Analizza questa conversazione e identifica il tema principale. "
                "Restituisci una singola parola chiave o tag (massimo 2 parole) che rappresenti l'argomento centrale. "
                "Esempi: 'amore', 'tecnologia', 'cucina', 'viaggi'. "
                "Rispondi solo con la tag.\n\n"
                f"Conversazione:\n{limited_history}"
            )
            
            response = cat.llm(prompt)
            tag = response.strip().lower()
            
            # Validazione tag
            if len(tag) > 50 or not tag:
                tag = "general"
            
            log.info(f"Tag estratto: {tag}")
            return tag
            
        except Exception as e:
            log.error(f"Errore estrazione tag: {e}")
            return "general"
    
    def get_note_filepath(self, tag: str) -> str:
        """Genera il percorso del file nota per una tag"""
        sanitized_tag = self.sanitize_tag(tag)
        return os.path.join(self.notes_dir, f"{sanitized_tag}.json")
    
    def load_existing_note(self, tag: str) -> Optional[Dict[str, Any]]:
        """Carica una nota esistente dal file JSON"""
        filepath = self.get_note_filepath(tag)
        
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    note_data = json.load(f)
                    log.info(f"Nota caricata per tag: {tag}")
                    return note_data
        except Exception as e:
            log.error(f"Errore caricamento nota per {tag}: {e}")
        
        return None
    
    def save_note(self, tag: str, note_content: str) -> bool:
        """Salva una nota nel file JSON"""
        filepath = self.get_note_filepath(tag)
        
        note_data = {
            "tag": tag,
            "note": note_content,
            "last_updated": datetime.now().isoformat(),
            "update_count": 1
        }
        
        # Se esiste già, incrementa il contatore
        existing = self.load_existing_note(tag)
        if existing:
            note_data["update_count"] = existing.get("update_count", 0) + 1
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(note_data, f, indent=2, ensure_ascii=False)
            
            log.info(f"Nota salvata per tag: {tag}")
            return True
            
        except Exception as e:
            log.error(f"Errore salvataggio nota per {tag}: {e}")
            return False
    
    def update_note_with_conversation(self, cat, tag: str, conversation_history: str) -> str:
        """Aggiorna la nota basandosi sulla conversazione corrente"""
        try:
            existing_note = self.load_existing_note(tag)
            previous_note = existing_note["note"] if existing_note else "Nessuna nota precedente."
            
            # Limita la cronologia
            limited_history = conversation_history[-PLUGIN_SETTINGS["max_history_chars"]:]
            
            prompt = (
                f"Basandoti sulla conversazione attuale e questa nota precedente: '{previous_note}', "
                f"crea una nota aggiornata di massimo {PLUGIN_SETTINGS['max_note_length']} parole che sintetizzi "
                f"le informazioni più importanti sull'argomento '{tag}'. "
                "Includi insights, fatti chiave e contesto utile per future conversazioni.\n\n"
                f"Conversazione attuale:\n{limited_history}"
            )
            
            updated_note = cat.llm(prompt)
            
            # Validazione lunghezza
            words = updated_note.split()
            if len(words) > PLUGIN_SETTINGS["max_note_length"]:
                updated_note = " ".join(words[:PLUGIN_SETTINGS["max_note_length"]])
            
            # Salva la nota aggiornata
            if self.save_note(tag, updated_note):
                return updated_note
            
        except Exception as e:
            log.error(f"Errore aggiornamento nota per {tag}: {e}")
        
        return ""
    
    def get_relevant_tag_for_response(self, cat, conversation_history: str) -> Optional[str]:
        """Determina quale tag è più rilevante per rispondere"""
        try:
            # Ottieni lista tag disponibili
            available_tags = self.get_available_tags()
            
            if not available_tags:
                return None
            
            limited_history = conversation_history[-PLUGIN_SETTINGS["max_history_chars"]:]
            
            prompt = (
                "Analizza questa conversazione e il messaggio dell'utente. "
                f"Quale argomento/tag tra questi sarebbe più utile per fornire una risposta contestuale: {', '.join(available_tags)}. "
                "Se nessuno è rilevante, rispondi 'nessuno'.\n\n"
                f"Conversazione:\n{limited_history}"
            )
            
            response = cat.llm(prompt).strip().lower()
            
            if response in available_tags and response != "nessuno":
                log.info(f"Tag rilevante identificato: {response}")
                return response
            
        except Exception as e:
            log.error(f"Errore identificazione tag rilevante: {e}")
        
        return None
    
    def get_contextual_note(self, tag: str) -> Optional[str]:
        """Recupera la nota per una tag specifica"""
        note_data = self.load_existing_note(tag)
        return note_data["note"] if note_data else None
    
    def get_available_tags(self) -> list:
        """Restituisce lista di tag disponibili"""
        try:
            if not os.path.exists(self.notes_dir):
                return []
            
            tags = []
            for filename in os.listdir(self.notes_dir):
                if filename.endswith('.json'):
                    tag = filename[:-5].replace('_', ' ')  # Rimuove .json e sostituisce _
                    tags.append(tag)
            
            return tags
            
        except Exception as e:
            log.error(f"Errore recupero tag disponibili: {e}")
            return []
    
    def cleanup_old_notes(self):
        """Rimuove note obsolete (implementazione futura)"""
        # TODO: Implementare pulizia basata su data e utilizzo
        pass

# Inizializza il manager globale
tags_manager = ContextualTagsManager()

@hook(priority=1)
def before_cat_sends_message(message, cat):
    """Hook eseguito prima che il cat invii un messaggio"""
    try:
        # Ottieni cronologia conversazione
        conversation_history = cat.stringify_chat_history()
        
        if not conversation_history:
            return message
        
        # Estrai tag dalla conversazione
        current_tag = tags_manager.extract_tag_from_conversation(cat, conversation_history)
        
        # Aggiorna/crea nota per questa tag
        updated_note = tags_manager.update_note_with_conversation(cat, current_tag, conversation_history)
        
        if updated_note:
            log.info(f"Nota aggiornata per tag '{current_tag}': {updated_note[:100]}...")
        
    except Exception as e:
        log.error(f"Errore in before_cat_sends_message: {e}")
    
    return message

@hook(priority=1)
def agent_prompt_prefix(prefix, cat):
    """Hook per aggiungere contesto al prompt dell'agente"""
    try:
        # Ottieni cronologia conversazione
        conversation_history = cat.stringify_chat_history()
        
        if not conversation_history:
            return prefix
        
        # Identifica tag rilevante per la risposta
        relevant_tag = tags_manager.get_relevant_tag_for_response(cat, conversation_history)
        
        if relevant_tag:
            # Recupera nota contestuale
            contextual_note = tags_manager.get_contextual_note(relevant_tag)
            
            if contextual_note:
                context_addition = f"\n\nInformazioni contestuali rilevanti su '{relevant_tag}':\n{contextual_note}\n"
                log.info(f"Aggiunto contesto per tag: {relevant_tag}")
                return prefix + context_addition
    
    except Exception as e:
        log.error(f"Errore in agent_prompt_prefix: {e}")
    
    return prefix

# Comandi utente per gestione tag
@hook
def before_cat_reads_message(user_message_json, cat):
    """Gestisce comandi utente per il sistema di tag"""
    message = user_message_json.get("text", "")
    
    if message.startswith("/show_tags"):
        available_tags = tags_manager.get_available_tags()
        if available_tags:
            response = f"🏷️ Tag disponibili ({len(available_tags)}):\n" + "\n".join([f"• {tag}" for tag in available_tags])
        else:
            response = "🏷️ Nessuna tag disponibile al momento."
        
        cat.send_ws_message(response, msg_type="chat")
        return {"text": ""}
    
    elif message.startswith("/show_note"):
        parts = message.split(" ", 1)
        if len(parts) > 1:
            tag = parts[1].strip().lower()
            note = tags_manager.get_contextual_note(tag)
            if note:
                response = f"📝 Nota per '{tag}':\n\n{note}"
            else:
                response = f"❌ Nessuna nota trovata per '{tag}'"
        else:
            response = "❓ Uso: /show_note [nome_tag]"
        
        cat.send_ws_message(response, msg_type="chat")
        return {"text": ""}
    
    elif message.startswith("/clear_notes"):
        try:
            # Rimuovi tutti i file note
            if os.path.exists(tags_manager.notes_dir):
                for filename in os.listdir(tags_manager.notes_dir):
                    if filename.endswith('.json'):
                        os.remove(os.path.join(tags_manager.notes_dir, filename))
            
            response = "🗑️ Tutte le note sono state eliminate."
        except Exception as e:
            response = f"❌ Errore eliminazione note: {e}"
        
        cat.send_ws_message(response, msg_type="chat")
        return {"text": ""}
    
    return user_message_json
