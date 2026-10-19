from django import forms

from products.forms import StyledModelForm

from .models import COMMENT_MAX_LENGTH, Review


class ReviewForm(StyledModelForm):
    """A star rating and a comment.

    The rating has no initial value, so a customer must pick one; the
    template draws the radios as DaisyUI stars. The comment strips
    whitespace, so a comment of only spaces counts as blank.

    Pass ``editor`` when editing: staff moderating someone else's review
    get no rating field, so they can never submit a rating change.
    """

    rating = forms.TypedChoiceField(
        choices=[(stars, stars) for stars in range(1, 6)],
        coerce=int,
        widget=forms.RadioSelect,
        error_messages={"required": "Choose a star rating."},
    )
    comment = forms.CharField(
        max_length=COMMENT_MAX_LENGTH,
        widget=forms.Textarea(attrs={"rows": 4}),
        error_messages={"required": "Write a comment to go with your rating."},
    )

    class Meta:
        model = Review
        fields = ["rating", "comment"]

    def __init__(self, *args, editor=None, **kwargs):
        super().__init__(*args, **kwargs)
        if editor is not None and self.instance.author_id != editor.pk:
            del self.fields["rating"]
