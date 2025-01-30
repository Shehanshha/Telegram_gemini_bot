from telegram.ext import JobQueue
from collections import defaultdict
from datetime import datetime, timedelta
from config import Config

class RateLimiter:
    def __init__(self):
        self.user_requests = defaultdict(list)
        
    def check_limit(self, user_id):
        now = datetime.now()
        user_requests = [t for t in self.user_requests[user_id] if now - t < timedelta(minutes=1)]
        self.user_requests[user_id] = user_requests
        
        if len(user_requests) >= Config.REQUEST_LIMIT:
            return False
        self.user_requests[user_id].append(now)
        return True

rate_limiter = RateLimiter()

def rate_limit(func):
    async def wrapper(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if not rate_limiter.check_limit(user_id):
            await update.message.reply_text("⚠️ Rate limit exceeded. Please wait 1 minute.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper