import asyncio
import datetime
import random

import discord

from app.core import Cog, Context, EDIT, REPLY, group, user_max_concurrency
from app.core.data import HistorySection, Question, QuestionSet, Stimulus
from app.util.types import CommandResponse, TypedInteraction
from app.util.views import UserView
from config import Colors


class MCQ(Cog):
    """Practice answering stimulus-based MCQs."""

    emoji = '🧠'

    @group('mcq', expand_subcommands=True)
    async def mcq(self, _ctx: Context) -> CommandResponse:
        """Practice answering a stimulus-based MCQ."""
        view = SingleMCQView(_ctx, sections=_ctx.bot.courses[0].sections)
        yield view.make_stimulus_embed(), view.make_question_embed(), view, REPLY
        await view.wait()

    @mcq.command('quiz', aliases=('q', 'exam', 'test'), hybrid=True)
    @user_max_concurrency(1)
    async def quiz(self, _ctx: Context) -> CommandResponse:
        """Practice answering a small set of MCQs with time-pressure."""
        view = MCQView(_ctx, sections=_ctx.bot.courses[0].sections)
        embed = discord.Embed(color=Colors.primary)
        embed.set_author(name=f'{_ctx.author.display_name}: MCQ', icon_url=_ctx.author.display_avatar)
        c = len(view.questions)
        embed.description = (
            f'This short MCQ consists of {c} questions.\nYou will have {c} minutes to answer all {c} questions.'
        )
        embed.add_field(
            name='Units Covered',
            value='\n'.join(
                f'- Period {s.period}: {s.range}' for s in sorted(view.raw_sections, key=lambda s: s.period)
            ),
        )
        embed.set_footer(text='Press the button below to begin.')
        yield embed, view, REPLY
        await view.submitted.wait()

        if view._timed_out:
            yield (
                'You ran out of time',
                view.make_results_embed(),
                view.make_stimulus_embed(),
                view.make_question_embed(),
                view,
                EDIT,
            )


class MCQStartButton(discord.ui.Button['MCQView']):
    def __init__(self) -> None:
        super().__init__(style=discord.ButtonStyle.green, label='Begin', row=0)

    async def callback(self, interaction: TypedInteraction) -> None:
        view = self.view
        view._timeout_task = view.ctx.bot.loop.create_task(view.timeout_task())
        expiry = discord.utils.utcnow() + datetime.timedelta(seconds=60 * len(view.questions))
        view.update_items()
        await interaction.response.edit_message(
            content=f'Quiz will end {discord.utils.format_dt(expiry, 'R')}',
            embeds=[view.make_stimulus_embed(), view.make_question_embed()],
            view=view
        )


class MCQAnswerChoice(discord.ui.Button['MCQView']):
    def __init__(self, choice_idx: int, *, style: discord.ButtonStyle, disabled: bool) -> None:
        super().__init__(style=style, disabled=disabled, label='ABCDE'[choice_idx], row=0)
        self.choice_idx: int = choice_idx

    async def callback(self, interaction: TypedInteraction) -> None:
        view = self.view
        view.user_choices[view.idx] = self.choice_idx
        view.update_items()
        embeds = [view.make_stimulus_embed(), view.make_question_embed()]
        await interaction.response.edit_message(embeds=embeds, view=view)


class MCQNav(discord.ui.Button['MCQView']):
    def __init__(self, offset: int, label: str, *, disabled: bool) -> None:
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label=label,
            disabled=disabled,
            row=1,
        )
        self.offset: int = offset

    async def callback(self, interaction: TypedInteraction) -> None:
        view = self.view
        view.idx += self.offset
        view.update_items()
        embeds = [view.make_results_embed()] if view._reveal else []
        embeds.extend((view.make_stimulus_embed(), view.make_question_embed()))
        await interaction.response.edit_message(embeds=embeds, view=view)


class MCQSubmit(discord.ui.Button['MCQView']):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs, row=1)

    async def callback(self, interaction: TypedInteraction) -> None:
        view = self.view
        view._reveal = True
        view.idx = 0
        view.update_items()
        embeds = [view.make_results_embed(), view.make_stimulus_embed(), view.make_question_embed()]
        view.submitted.set()
        await interaction.response.edit_message(content='', embeds=embeds, view=view)


class MCQView(UserView):
    def __init__(self, ctx: Context, *, sections: list[HistorySection]) -> None:
        self.ctx: Context = ctx
        self.raw_sections: list[HistorySection] = random.choices(sections, k=3)
        self.sections: list[HistorySection] = []

        buffer = 1
        self.stimulus_spans: list[(int, int)] = []
        question_sets = dict[QuestionSet, None]()
        for section in self.raw_sections:
            while True:
                candidate = random.choice(section.mcqs)
                if candidate not in question_sets:
                    question_sets[candidate] = None
                    self.stimulus_spans.extend(
                        [(buffer, buffer + len(candidate.questions) - 1)] * len(candidate.questions)
                    )
                    self.sections.extend([section] * len(candidate.questions))
                    buffer += len(candidate.questions)
                    break

        self.questions: list[(Stimulus, Question)] = [(s.stimulus, q) for s in question_sets for q in s.questions]
        self.choices: list[(list[str], int)] = []
        for _, question in self.questions:
            choices = [question.answer, *question.other_choices]
            random.shuffle(choices)
            self.choices.append((choices, choices.index(question.answer)))

        self.user_choices: list[int | None] = [None] * len(self.questions)
        self.idx: int = 0
        self._reveal: bool = False
        self._timed_out: bool = False
        self._timeout_task: asyncio.Task | None = None
        self.submitted: asyncio.Event = asyncio.Event()

        super().__init__(ctx.author, timeout=None)
        self.add_item(MCQStartButton())

    @property
    def stimulus(self) -> Stimulus:
        return self.questions[self.idx][0]

    @property
    def question(self) -> Question:
        return self.questions[self.idx][1]

    @property
    def embed_color(self) -> int:
        if not self._reveal:
            return Colors.primary
        return Colors.success if self.user_choices[self.idx] == self.choices[self.idx][1] else Colors.error

    def update_items(self) -> None:
        self.clear_items()
        choices, correct_idx = self.choices[self.idx]
        for choice_idx in range(len(choices)):
            if self._reveal:
                style = discord.ButtonStyle.success if choice_idx == correct_idx else discord.ButtonStyle.secondary
                if self.user_choices[self.idx] == choice_idx != correct_idx:
                    style = discord.ButtonStyle.danger
            else:
                style = (
                    discord.ButtonStyle.primary
                    if self.user_choices[self.idx] == choice_idx else discord.ButtonStyle.secondary
                )
            self.add_item(MCQAnswerChoice(choice_idx, style=style, disabled=self._reveal))

        self.add_item(MCQNav(-1, 'Previous', disabled=self.idx == 0))
        self.add_item(MCQNav(1, 'Next', disabled=self.idx == len(self.questions) - 1))
        if not self._reveal:
            self.add_item(
                MCQSubmit(label='Quit', style=discord.ButtonStyle.danger) if None in self.user_choices
                else MCQSubmit(label='Submit', style=discord.ButtonStyle.primary)
            )

    @property
    def correct(self) -> int:
        return sum(
            1 for user_choice, (_, correct_idx) in zip(self.user_choices, self.choices) if user_choice == correct_idx
        )

    def make_results_embed(self) -> discord.Embed:
        embed = discord.Embed(color=Colors.primary)
        ratio = self.correct / len(self.questions)
        embed.description = f'Score: {self.correct}/{len(self.questions)} ({ratio:.1%})'
        return embed

    def make_stimulus_embed(self) -> discord.Embed:
        embed = discord.Embed(color=self.embed_color)
        embed.set_author(
            name=f'{self.ctx.author.display_name}: Question {self.idx + 1}/{len(self.questions)}',
            icon_url=self.ctx.author.display_avatar,
        )

        start, end = self.stimulus_spans[self.idx]
        header = f'Question {start} refers' if start == end else f'Questions {start}-{end} refer'
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
            if self._reveal:
                if choice == self.question.answer:
                    return f'**{choice}**'
                user_choice = self.user_choices[self.idx]
                if user_choice and choice == self.choices[self.idx][0][user_choice]:
                    return f'~~{choice}~~'
            return choice

        embed = discord.Embed(color=self.embed_color, timestamp=self.ctx.now)
        embed.add_field(
            name=f'**{self.question.question}**',
            value='\n'.join(f'- {letter}) {fmt(choice)}' for letter, choice in zip('ABCDE', self.choices[self.idx][0])),
        )

        if self._reveal and self.question.explanation:
            embed.add_field(name='Explanation', value=self.question.explanation, inline=False)

        section = self.sections[self.idx]
        embed.set_footer(text=f'Period {section.period}: {section.range}')
        return embed

    async def timeout_task(self) -> None:
        await asyncio.sleep(60 * len(self.questions))
        self._timed_out = True
        self._reveal = True
        self.idx = 0
        self.update_items()
        self.submitted.set()


class SingleMCQAnswerChoice(discord.ui.Button['SingleMCQView']):
    def __init__(self, choice_idx: int, choice: str) -> None:
        super().__init__(style=discord.ButtonStyle.primary, label='ABCDE'[choice_idx], row=0)
        self.choice_idx: int = choice_idx
        self.choice: str = choice

    async def callback(self, interaction: TypedInteraction) -> None:
        view = self.view
        view.user_choice = self.choice
        view.is_correct = self.choice == view.question.answer

        for item in view.children:
            if isinstance(item, SingleMCQAnswerChoice):
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


class SingleMCQView(UserView):
    def __init__(self, ctx: Context, *, sections: list[HistorySection]) -> None:
        self.ctx: Context = ctx
        self._sections: list[HistorySection] = sections
        self.question_number: int = 1

        self.user_choice: str | None = None
        self.is_correct: bool | None = None

        super().__init__(ctx.author, timeout=900)
        self.section: HistorySection = random.choice(self._sections)
        self.question_set: QuestionSet = random.choice(self.section.mcqs)
        self.question: Question = random.choice(self.question_set.questions)
        self._initial_question_number: int = self.question_number
        self.shuffle_choices()

    def shuffle_choices(self) -> None:
        self.choices = [self.question.answer, *self.question.other_choices]
        random.shuffle(self.choices)

        self.clear_items()
        for idx, choice in enumerate(self.choices):
            self.add_item(SingleMCQAnswerChoice(idx, choice))

    @property
    def stimulus(self) -> Stimulus:
        return self.question_set.stimulus

    @property
    def embed_color(self) -> int:
        if self.is_correct is None:
            return Colors.primary
        return Colors.success if self.is_correct else Colors.error

    def make_stimulus_embed(self) -> discord.Embed:
        embed = discord.Embed(color=self.embed_color)
        embed.set_author(name=f'{self.ctx.author.display_name}: MCQ', icon_url=self.ctx.author.display_avatar)

        embed.description = f'**This question refers {self.stimulus.header}**'

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
            name=f'**{self.question.question}**',
            value='\n'.join(f'- {letter}) {fmt(choice)}' for letter, choice in zip('ABCDE', self.choices)),
        )

        if self.is_correct is not None and self.question.explanation:
            embed.add_field(name='Explanation', value=self.question.explanation, inline=False)

        embed.set_footer(text=f'Period {self.section.period}: {self.section.range}')
        return embed


setup = MCQ.simple_setup
