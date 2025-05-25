
# Plugin metadata
@plugin
def settings_schema():
    return {
        "title": "Sistema Tag Dinamiche",
        "type": "object",
        "properties": {
            "enabled": {
                "title": "Abilita sistema tag",
                "type": "boolean",
                "default": True
            },
            "max_notes": {
                "title": "Numero massimo note",
                "type": "integer",
                "default": 100,
                "minimum": 10,
                "maximum": 1000
            },
            "max_note_length": {
                "title": "Lunghezza massima note (parole)",
                "type": "integer", 
                "default": 200,
                "minimum": 50,
                "maximum": 500
            }
        }
    }

# Inizializzazione plugin
log.info("🏷️ Plugin Sistema Tag Dinamiche caricato con successo!")
log.info(f"📁 Directory note: {tags_manager.notes_dir}")
log.info("💡 Comandi disponibili: /show_tags, /show_note [tag], /clear_notes")
