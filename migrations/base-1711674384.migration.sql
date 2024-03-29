CREATE TABLE IF NOT EXISTS sections_enabled (
    user_id BIGINT NOT NULL,
    course TEXT NOT NULL,
    sections INTEGER[],
    PRIMARY KEY (user_id, course)
);

-- MASTERY: 0 = not studied, 1 = needs practice, 2 = fluent, 3 = super fluent, 4+ = mastered
-- if correct, mastery += 1
-- if incorrect at 1, 2, or 3, set to 1
-- if incorrect at 4+, decrease mastery by 1
CREATE TABLE IF NOT EXISTS terms_studied (
    user_id BIGINT NOT NULL,
    term_hash BIGINT NOT NULL,
    mastery INTEGER NOT NULL DEFAULT 0
);