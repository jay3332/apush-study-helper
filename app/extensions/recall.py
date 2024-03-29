from app.core import Cog, Context, group, user_max_concurrency
from app.util.types import CommandResponse
from app.util.views import UserView


class Recall(Cog):
    """Practice recalling terms and definitions."""

    @group('recall')
    async def recall(self, _ctx: Context) -> CommandResponse:
        """Practice recalling terms and definitions."""
        return 'hi'

    @recall.command('term', aliases=('t', 'word'), hybrid=True)
    @user_max_concurrency(1)
    async def recall_term(self, _ctx: Context) -> CommandResponse:
        """Recall a term by its definition."""
        return 'hi'


setup = Recall.simple_setup
