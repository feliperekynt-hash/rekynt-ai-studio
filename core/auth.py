import os
import json

class BrokerAuthManager:
    """
    Gerenciador de Acesso da Equipe de Corretores Rekynt Imóveis.
    Mantém a lista VIP dos 6 corretores autorizados a usar o estúdio.
    """
    def __init__(self, config_dir=None):
        self.base_dir = r"C:\Users\fenie\.gemini\antigravity\scratch\rekynt_reels_ai_studio"
        self.config_dir = config_dir or os.path.join(self.base_dir, "config")
        os.makedirs(self.config_dir, exist_ok=True)
        
        self.config_file = os.path.join(self.config_dir, "corretores_autorizados.json")
        self._ensure_default_config()

    def _ensure_default_config(self):
        if not os.path.exists(self.config_file):
            default_brokers = [
                "corretor.rekynt@gmail.com",
                "corretor1@gmail.com",
                "corretor2@gmail.com",
                "corretor3@gmail.com",
                "corretor4@gmail.com",
                "corretor5@gmail.com",
                "corretor6@gmail.com"
            ]
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(default_brokers, f, indent=2, ensure_ascii=False)

    def get_authorized_brokers(self):
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return ["corretor.rekynt@gmail.com"]

    def is_authorized(self, email):
        if not email:
            return False
        authorized = [e.lower().strip() for e in self.get_authorized_brokers()]
        return email.lower().strip() in authorized

    def add_broker(self, email):
        brokers = self.get_authorized_brokers()
        email_clean = email.lower().strip()
        if email_clean not in [e.lower().strip() for e in brokers]:
            brokers.append(email_clean)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(brokers, f, indent=2, ensure_ascii=False)
            return True
        return False
