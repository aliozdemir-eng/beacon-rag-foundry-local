# Prompt Engineering for Grounded Question Answering

When a language model is given retrieved context and asked a question, the
system prompt is what decides whether it behaves like a careful research
assistant or a confident guesser. A few instructions matter more than the
rest for this use case.

First, tell the model explicitly to answer only from the provided context,
and to say it doesn't know when the context doesn't contain the answer.
Without this instruction, a capable model will often fill gaps with
plausible-sounding but unsupported details, because that is what it was
trained to do in open-ended conversation.

Second, ask the model to name which source it used. Even a simple instruction
like "list the document names you relied on" makes it much easier for a user
to verify an answer, and makes it obvious when the model ignored the context
it was given.

Third, keep answers concise by default. Long, hedged answers are harder to
verify at a glance; a short, direct answer followed by a source reference is
usually more useful for a Q&A assistant than a long essay.

## System prompt vs. user prompt

In a chat-style API, the system message sets the assistant's role and rules
once per conversation, while the user message carries the actual question
plus the retrieved context for that specific turn. Splitting them this way
keeps the instructions stable even as the retrieved context changes from one
question to the next.
