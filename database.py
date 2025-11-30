import json
import os
from datetime import datetime, timedelta
import threading

class Database:
    def __init__(self):
        self.file = 'data.json'
        self.lock = threading.Lock()
        self.load()
    
    def load(self):
        if os.path.exists(self.file):
            try:
                with open(self.file, 'r') as f:
                    self.data = json.load(f)
            except:
                self.data = self._default()
        else:
            self.data = self._default()
            self.save()
    
    def _default(self):
        return {
            'users': {}, 'banned': [], 'pending_payments': [],
            'cloned_bots': {}, 'message_map': {}, 'awaiting_token': {},
            'clone_bot_users': {}, 'clone_bot_messages': {},
            'paid_batches_text': 'No batches available yet.',
            'greetings': ["✅ Message sent!", "✨ Forwarded!", "📨 Delivered!", "👍 Owner will see!", "🎯 Sent!"]
        }
    
    def save(self):
        with self.lock:
            with open(self.file, 'w') as f:
                json.dump(self.data, f, indent=2)
    
    def add_user(self, uid, username, fname):
        s = str(uid)
        if s not in self.data['users']:
            self.data['users'][s] = {'id': uid, 'username': username, 'name': fname, 'joined': datetime.now().isoformat(), 'is_active': True}
            self.save()
    
    def get_user(self, uid):
        return self.data['users'].get(str(uid))
    
    def get_all_users(self):
        return self.data['users']
    
    def get_active_users(self):
        return {k: v for k, v in self.data['users'].items() if v.get('is_active', True)}
    
    def get_banned_users(self):
        return {k: v for k, v in self.data['users'].items() if int(k) in self.data['banned']}
    
    def ban_user(self, uid):
        if uid not in self.data['banned']:
            self.data['banned'].append(uid)
            if str(uid) in self.data['users']:
                self.data['users'][str(uid)]['is_active'] = False
            self.save()
    
    def unban_user(self, uid):
        if uid in self.data['banned']:
            self.data['banned'].remove(uid)
            if str(uid) in self.data['users']:
                self.data['users'][str(uid)]['is_active'] = True
            self.save()
    
    def is_banned(self, uid):
        return uid in self.data['banned']
    
    def add_pending_payment(self, user_id, plan_days, plan_price, screenshot):
        payment = {'id': len(self.data['pending_payments']) + 1, 'user_id': user_id, 'plan_days': plan_days, 'plan_price': plan_price, 'screenshot': screenshot, 'time': datetime.now().isoformat(), 'status': 'pending'}
        self.data['pending_payments'].append(payment)
        self.save()
        return payment
    
    def get_pending_payments(self):
        return [p for p in self.data['pending_payments'] if p['status'] == 'pending']
    
    def approve_payment(self, payment_id):
        for p in self.data['pending_payments']:
            if p['id'] == payment_id:
                p['status'] = 'approved'
                self.save()
                return p
        return None
    
    def reject_payment(self, payment_id):
        for p in self.data['pending_payments']:
            if p['id'] == payment_id:
                p['status'] = 'rejected'
                self.save()
                return True
        return False
    
    def set_awaiting_token(self, user_id, payment_data):
        self.data['awaiting_token'][str(user_id)] = payment_data
        self.save()
    
    def is_awaiting_token(self, user_id):
        return str(user_id) in self.data['awaiting_token']
    
    def get_awaiting_token_data(self, user_id):
        return self.data['awaiting_token'].get(str(user_id))
    
    def remove_awaiting_token(self, user_id):
        if str(user_id) in self.data['awaiting_token']:
            del self.data['awaiting_token'][str(user_id)]
            self.save()
    
    def add_cloned_bot(self, user_id, bot_token, plan_days, bot_username):
        expiry = datetime.now() + timedelta(days=plan_days)
        self.data['cloned_bots'][str(user_id)] = {'bot_token': bot_token, 'bot_username': bot_username, 'owner_id': user_id, 'created': datetime.now().isoformat(), 'expiry': expiry.isoformat(), 'plan_days': plan_days, 'active': True}
        self.save()
    
    def get_cloned_bot(self, user_id):
        bot = self.data['cloned_bots'].get(str(user_id))
        if bot and bot['active']:
            expiry = datetime.fromisoformat(bot['expiry'])
            if datetime.now() > expiry:
                bot['active'] = False
                self.save()
                return None
            return bot
        return None
    
    def get_all_active_cloned_bots(self):
        active_bots = {}
        for owner_id, bot in self.data['cloned_bots'].items():
            if bot.get('active', False):
                try:
                    expiry = datetime.fromisoformat(bot['expiry'])
                    if datetime.now() <= expiry:
                        active_bots[owner_id] = bot
                    else:
                        bot['active'] = False
                except:
                    pass
        self.save()
        return active_bots
    
    def add_clone_bot_user(self, clone_owner_id, user_id, username, fname):
        clone_key = str(clone_owner_id)
        if clone_key not in self.data['clone_bot_users']:
            self.data['clone_bot_users'][clone_key] = {}
        self.data['clone_bot_users'][clone_key][str(user_id)] = {'id': user_id, 'username': username, 'name': fname, 'joined': datetime.now().isoformat()}
        self.save()
    
    def get_clone_bot_users(self, clone_owner_id):
        return self.data['clone_bot_users'].get(str(clone_owner_id), {})
    
    def map_clone_message(self, clone_owner_id, user_id, owner_msg_id):
        clone_key = str(clone_owner_id)
        if clone_key not in self.data['clone_bot_messages']:
            self.data['clone_bot_messages'][clone_key] = {}
        self.data['clone_bot_messages'][clone_key][str(owner_msg_id)] = user_id
        self.save()
    
    def get_clone_user_from_msg(self, clone_owner_id, owner_msg_id):
        clone_key = str(clone_owner_id)
        if clone_key in self.data['clone_bot_messages']:
            return self.data['clone_bot_messages'][clone_key].get(str(owner_msg_id))
        return None
    
    def map_message(self, user_id, owner_msg_id):
        self.data['message_map'][str(owner_msg_id)] = user_id
        self.save()
    
    def get_user_from_msg(self, owner_msg_id):
        return self.data['message_map'].get(str(owner_msg_id))
    
    def get_random_greeting(self):
        import random
        return random.choice(self.data['greetings'])
    
    def set_paid_batches(self, text):
        self.data['paid_batches_text'] = text
        self.save()
    
    def get_paid_batches(self):
        return self.data['paid_batches_text']

db = Database()
