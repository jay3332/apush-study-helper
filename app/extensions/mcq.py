import random

import discord

from app.core import Cog, Context, EDIT, group, user_max_concurrency
from app.core.data import HistorySection, Question, QuestionSet, Stimulus
from app.util.types import CommandResponse, TypedInteraction
from app.util.views import UserView
from config import Colors


class MCQ(Cog):
    """Practice answering stimulus-based MCQs."""

    @group('mcq')
    async def mcq(self, _ctx: Context) -> CommandResponse:
        """Practice answering a stimulus-based MCQ."""
        view = MCQView(_ctx, sections=_ctx.bot.courses[0].sections, orderly=False)
        yield view.make_stimulus_embed(), view.make_question_embed(), view
        await view.wait()

    @mcq.command('quiz', aliases=('q', 'exam', 'test'), hybrid=True)
    @user_max_concurrency(1)
    async def quiz(self, _ctx: Context) -> CommandResponse:
        """Practice answering a small set of MCQs with time-pressure."""
        return 'hi'


class MCQAnswerChoice(discord.ui.Button['MCQView']):
    def __init__(self, choice_idx: int, choice: str) -> None:
        super().__init__(style=discord.ButtonStyle.primary, label='ABCDE'[choice_idx], row=0)
        self.choice_idx: int = choice_idx
        self.choice: str = choice

    async def callback(self, interaction: TypedInteraction) -> None:
        view = self.view
        view.user_choice = self.choice
        view.is_correct = self.choice == view.question.answer

        for item in view.children:
            if isinstance(item, MCQAnswerChoice):
                item.disabled = True
                item.style = (
                    discord.ButtonStyle.success
                    if item.choice == view.question.answer
                    else discord.ButtonStyle.secondary
                )
        if not view.is_correct:
            self.style = discord.ButtonStyle.danger

        embeds = [view.make_stimulus_embed(), view.make_question_embed()]
        await interaction.response.edit_message(embeds=embeds, view=view)
        view.stop()


class MCQView(UserView):
    def __init__(self, ctx: Context, *, sections: list[HistorySection], orderly: bool) -> None:
        self.ctx: Context = ctx
        self._sections: list[HistorySection] = sections
        self._orderly: bool = orderly
        self.question_number: int = 1

        self.user_choice: str | None = None
        self.is_correct: bool | None = None

        super().__init__(ctx.author, timeout=900)
        self.next_question_set()
        self.shuffle_choices()

    def next_question_set(self) -> None:
        self.section: HistorySection = random.choice(self._sections)
        self.question_set: QuestionSet = random.choice(self.section.mcqs)
        self.idx: int = 0 if self._orderly else random.randrange(len(self.question_set.questions))
        self._initial_question_number: int = self.question_number

    def next_question(self) -> None:
        self.question_number += 1
        if self._orderly:
            if self.idx + 1 >= len(self.question_set.stimulus):
                self.next_question_set()
            else:
                self.idx += 1
            return

        self.next_question_set()

    def shuffle_choices(self) -> None:
        self.choices = [self.question.answer, *self.question.other_choices]
        random.shuffle(self.choices)

        self.clear_items()
        for idx, choice in enumerate(self.choices):
            self.add_item(MCQAnswerChoice(idx, choice))

    @property
    def stimulus(self) -> Stimulus:
        return self.question_set.stimulus

    @property
    def question(self) -> Question:
        return self.question_set.questions[self.idx]

    @property
    def embed_color(self) -> int:
        if self.is_correct is None:
            return Colors.primary
        return Colors.success if self.is_correct else Colors.error

    def make_stimulus_embed(self) -> discord.Embed:
        embed = discord.Embed(color=self.embed_color)
        embed.set_author(name=f'{self.ctx.author.display_name}: MCQ', icon_url=self.ctx.author.display_avatar)

        if self._orderly:
            header = f'Question {self.question_number} refers' if len(self.question_set.questions) == 1 else (
                f'Questions {self._initial_question_number}-'
                f'{self._initial_question_number + len(self.question_set.questions) - 1} refer'
            )
        else:
            header = f'This question refers'
        embed.description = f'**{header} {self.stimulus.header}**'

        if self.stimulus.image:
            embed.set_image(url=self.stimulus.image)
        else:
            embed.description += '\n\n' + self.stimulus.text

        if self.stimulus.footer:
            embed.set_footer(text=self.stimulus.footer)

        return embed

    def make_question_embed(self) -> discord.Embed:
        def fmt(choice: str) -> str:
            if self.is_correct is not None and choice == self.question.answer:
                return f'**{choice}**'
            if choice == self.user_choice:
                return f'~~{choice}~~'
            return choice

        embed = discord.Embed(color=self.embed_color, timestamp=self.ctx.now)
        embed.add_field(
            name=f'{f'{self._initial_question_number}. ' if self._orderly else ""}**{self.question.question}**',
            value='\n'.join(f'- {letter}) {fmt(choice)}' for letter, choice in zip('ABCDE', self.choices)),
        )

        if self.is_correct is not None and self.question.explanation:
            embed.add_field(name='Explanation', value=self.question.explanation, inline=False)

        embed.set_footer(text=f'Period {self.section.period}: {self.section.range}')
        return embed


setup = MCQ.simple_setup
