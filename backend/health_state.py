from __future__ import annotations

from pydantic import BaseModel, Field


class HealthProfile(BaseModel):
    """Complete stored health profile for a user."""

    ldl: float | None = None
    hdl: float | None = None
    triglycerides: float | None = None
    total_cholesterol: float | None = None
    vitamin_d: float | None = None
    b12: float | None = None
    tsh: float | None = None
    ferritin: float | None = None
    fasting_glucose: float | None = None
    hba1c: float | None = None
    hemoglobin: float | None = None
    creatinine: float | None = None
    sgpt_alt: float | None = None
    sgot_ast: float | None = None
    weight_kg: float | None = None
    bmi: float | None = None
    bmr: float | None = None
    body_fat_pct: float | None = None
    visceral_fat_kg: float | None = None
    muscle_mass_kg: float | None = None
    body_water_pct: float | None = None
    protein_kg: float | None = None
    bone_mass_kg: float | None = None
    body_age_device: int | None = None
    resting_hr: float | None = None
    hrv_ms: float | None = None
    steps_today: int | None = None
    steps_avg_7d: int | None = None
    active_energy_kcal: float | None = None
    exercise_min: int | None = None
    sleep_hours: float | None = None
    sleep_deep_pct: float | None = None
    sleep_rem_pct: float | None = None
    vo2max: float | None = None
    respiratory_rate: float | None = None
    walking_asymmetry_pct: float | None = None
    flights_climbed: int | None = None
    blood_oxygen_pct: float | None = None
    blood_pressure_systolic: float | None = None
    blood_pressure_diastolic: float | None = None
    face_age: float | None = None
    posture_score_pct: float | None = None
    temperature_c: float | None = None
    humidity_pct: float | None = None
    aqi: int | None = None
    uv_index: float | None = None
    phq9_score: int | None = None
    phq9_last_calibrated_at: str | None = None
    stress_level: int | None = None
    screen_time_hours: float | None = None
    academic_gpa: float | None = None
    study_hours_daily: float | None = None
    exam_stress: int | None = None
    academic_year: str | None = None
    family_diabetes: bool = False
    family_heart: bool = False
    family_hypertension: bool = False
    family_mental: bool = False
    exercise_hours_week: float | None = None
    sleep_target: float | None = None
    smoking: str = "never"
    diet_quality: str = "average"
    age: int | None = None
    sex: str | None = None
    height_cm: float | None = None
    family_id: str | None = None
    last_blood_report_date: str | None = None
    last_vitd_test_date: str | None = None
    last_glucose_test_date: str | None = None
    last_general_checkup_date: str | None = None
    doctor_name: str | None = None
    doctor_email: str | None = None
    doctor_phone: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    location_label: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    bio_age_overall: float | None = None
    bio_age_cardiovascular: float | None = None
    bio_age_metabolic: float | None = None
    bio_age_musculoskeletal: float | None = None
    bio_age_neurological: float | None = None
    mental_wellness_score: float | None = None
    updated_at: str | None = None


class UserCreate(BaseModel):
    """Request body for creating a user."""

    id: str
    name: str
    age: int | None = None
    sex: str | None = None
    height_cm: float | None = None


class MealEntry(BaseModel):
    """A single meal log entry."""

    description: str | None = None
    photo_path: str | None = None
    calories: float | None = None
    protein_g: float | None = None
    carbs_g: float | None = None
    fat_g: float | None = None
    saturated_fat_g: float | None = None
    fiber_g: float | None = None
    vitamin_d_ug: float | None = None
    b12_ug: float | None = None
    health_score: float | None = None
    ai_notes: str | None = None


class WorkoutEntry(BaseModel):
    """A single workout log entry."""

    type: str
    duration_min: int | None = None
    calories: float | None = None
    source: str = "manual"
    date: str


class WaterEntry(BaseModel):
    """A water intake log entry."""

    amount_ml: int


class PostureEntry(BaseModel):
    """A posture reading."""

    score_pct: float
    avg_angle: float | None = None
    is_slouching: bool = False


class SpotifyEntry(BaseModel):
    """Spotify listening analysis entry."""

    avg_valence: float | None = None
    avg_energy: float | None = None
    avg_danceability: float | None = None
    track_count: int | None = None
    baseline_valence: float | None = None


class GamificationState(BaseModel):
    """Current gamification state for a user."""

    current_streak: int = 0
    longest_streak: int = 0
    total_xp: int = 0
    level: int = 1
    level_name: str = "Health Rookie"
    today_actions: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    active_challenge: dict | None = None


class FamilyCreate(BaseModel):
    """Request body for creating a family group."""

    name: str


class FamilyJoin(BaseModel):
    """Request body for joining a family group."""

    join_code: str
    relationship: str
    privacy_level: str = "summary"
