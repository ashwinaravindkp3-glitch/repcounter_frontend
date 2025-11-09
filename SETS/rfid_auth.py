# rfid_auth.py
from typing import Tuple, Optional

class RFIDAuth:
    def __init__(self, rfid_users: dict):
        self.rfid_users = rfid_users
        self.current_user: Optional[str] = None
    
    def parse_uid_message(self, message: str) -> Optional[str]:
        if message.startswith("UID_REQ|"):
            return message.split('|')[1]
        return None
    
    def validate_user(self, uid_with_spaces: str) -> Tuple[bool, Optional[str]]:
        uid_clean = uid_with_spaces.replace(' ', '')[:8]
        if uid_clean in self.rfid_users:
            return True, self.rfid_users[uid_clean]
        return False, None
    
    def login(self, uid_with_spaces: str) -> Tuple[bool, Optional[str]]:
        is_valid, username = self.validate_user(uid_with_spaces)
        if is_valid:
            self.current_user = username
            return True, username
        return False, None
    
    def logout(self):
        self.current_user = None
    
    def get_current_user(self) -> Optional[str]:
        return self.current_user