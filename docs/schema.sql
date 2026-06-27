CREATE TABLE frames (
    frame_id BIGINT PRIMARY KEY,
    segment_name TEXT NOT NULL,
    frame_index INTEGER NOT NULL,
    prototype_id TEXT NOT NULL,
    collection_version TEXT NOT NULL,
    weather TEXT NOT NULL CHECK (weather IN ('晴天', '阴天', '雨天')),
    time_of_day TEXT NOT NULL CHECK (time_of_day IN ('白天', '晚上')),
    view_direction TEXT NOT NULL CHECK (view_direction IN ('前', '后', '左', '右')),
    value_score INTEGER NOT NULL CHECK (value_score BETWEEN 1 AND 10),
    dataset_split TEXT NOT NULL CHECK (dataset_split IN ('训练集', '验证集', '测试集')),
    model_inference TEXT NOT NULL DEFAULT '',
    data_path TEXT NOT NULL,
    target_tags TEXT NOT NULL DEFAULT '',
    noise_tags TEXT NOT NULL DEFAULT '',
    UNIQUE (segment_name, frame_index)
);

CREATE TABLE dataset_versions (
    id BIGINT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE dataset_version_frames (
    dataset_version_id BIGINT NOT NULL REFERENCES dataset_versions(id),
    frame_id BIGINT NOT NULL REFERENCES frames(frame_id),
    split TEXT NOT NULL CHECK (split IN ('train', 'val', 'test')),
    PRIMARY KEY (dataset_version_id, frame_id)
);

CREATE INDEX idx_frames_segment_frame ON frames(segment_name, frame_index);
CREATE INDEX idx_frames_prototype ON frames(prototype_id);
CREATE INDEX idx_frames_collection_version ON frames(collection_version);
CREATE INDEX idx_frames_weather ON frames(weather);
CREATE INDEX idx_frames_time_of_day ON frames(time_of_day);
CREATE INDEX idx_frames_view_direction ON frames(view_direction);
CREATE INDEX idx_frames_value_score ON frames(value_score);
CREATE INDEX idx_frames_dataset_split ON frames(dataset_split);
