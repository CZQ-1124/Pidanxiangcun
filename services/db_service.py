import sqlite3
import pandas as pd
from config.settings import DB_PATH, SEED_XLSX, SEED_CSV


def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_column(conn, table: str, col: str, ddl: str):
    cols = {r['name'] for r in conn.execute(f'PRAGMA table_info({table})').fetchall()}
    if col not in cols:
        conn.execute(f'ALTER TABLE {table} ADD COLUMN {col} {ddl}')


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS patients (
            person_id TEXT PRIMARY KEY,
            person_name TEXT NOT NULL,
            role_bind_hint TEXT,
            family_contact TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS cases (
            visit_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            person_id TEXT NOT NULL,
            person_name TEXT NOT NULL,
            uploader_name TEXT,
            source_role TEXT,
            image_path TEXT,
            body_part TEXT,
            duration TEXT,
            itch INTEGER DEFAULT 0,
            pain INTEGER DEFAULT 0,
            bleeding INTEGER DEFAULT 0,
            growth INTEGER DEFAULT 0,
            history TEXT,
            image_quality TEXT,
            quality_ok INTEGER DEFAULT 1,
            quality_message TEXT,
            ai_visual_summary TEXT,
            ai_candidates TEXT,
            ai_confidence TEXT,
            risk_level TEXT,
            risk_score INTEGER,
            action_advice TEXT,
            trend_summary TEXT,
            doctor_review_label TEXT,
            doctor_review_risk TEXT,
            final_outcome TEXT,
            final_diagnosis TEXT,
            is_training_case INTEGER DEFAULT 0,
            expert_treatment_plan TEXT,
            expert_followup_plan TEXT,
            expert_reviewer TEXT,
            expert_reviewed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS seed_cases (
            case_id TEXT PRIMARY KEY,
            image_id INTEGER,
            patient_id_anon TEXT,
            file_name TEXT,
            relative_path TEXT,
            source_batch TEXT,
            original_group TEXT,
            use_tag TEXT,
            disease_level1 TEXT,
            disease_level2 TEXT,
            working_label TEXT,
            final_confirmed_diagnosis TEXT,
            diagnosis_status TEXT,
            pathology_confirmed TEXT,
            body_site TEXT,
            image_type TEXT,
            image_quality TEXT,
            is_typical_case TEXT,
            danger_signal TEXT,
            referral_level TEXT,
            suspected_diagnosis_1 TEXT,
            suspected_diagnosis_2 TEXT,
            common_misdiagnosis TEXT,
            symptom_keywords TEXT,
            teaching_point TEXT,
            gold_explanation TEXT,
            usable_for_quiz TEXT,
            village_doctor_level TEXT,
            note TEXT,
            urgency_score REAL,
            split_suggestion TEXT,
            system_priority TEXT,
            doctor_review_label TEXT,
            doctor_review_risk TEXT,
            is_training_case INTEGER DEFAULT 1,
            review_status TEXT DEFAULT '待专家复核'
        );

        CREATE TABLE IF NOT EXISTS audio_notes (
            note_id TEXT PRIMARY KEY,
            person_id TEXT,
            person_name TEXT,
            visit_id TEXT,
            audio_path TEXT,
            transcript_text TEXT,
            summary_text TEXT,
            structured_json TEXT,
            created_by TEXT,
            created_role TEXT,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS training_attempts (
            attempt_id TEXT PRIMARY KEY,
            training_type TEXT,
            learner_name TEXT,
            learner_role TEXT,
            question_payload TEXT,
            user_answer TEXT,
            ai_feedback TEXT,
            score REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS review_queue (
            submission_id TEXT PRIMARY KEY,
            source_type TEXT,
            source_id TEXT,
            patient_name TEXT,
            submitted_by TEXT,
            submitted_role TEXT,
            note TEXT,
            status TEXT DEFAULT '待专家复核',
            expert_treatment_plan TEXT,
            expert_followup_plan TEXT,
            expert_reviewer TEXT,
            expert_review_note TEXT,
            final_label TEXT,
            final_risk TEXT,
            expert_reviewed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    for col, ddl in [
        ('expert_treatment_plan', 'TEXT'),
        ('expert_followup_plan', 'TEXT'),
        ('expert_reviewer', 'TEXT'),
        ('expert_reviewed_at', 'TIMESTAMP'),
    ]:
        _ensure_column(conn, 'cases', col, ddl)
    for col, ddl in [
        ('expert_treatment_plan', 'TEXT'),
        ('expert_followup_plan', 'TEXT'),
        ('expert_reviewer', 'TEXT'),
        ('expert_review_note', 'TEXT'),
        ('final_label', 'TEXT'),
        ('final_risk', 'TEXT'),
        ('expert_reviewed_at', 'TIMESTAMP'),
    ]:
        _ensure_column(conn, 'review_queue', col, ddl)
    conn.commit()
    conn.close()


def import_seed_cases(force: bool = False):
    init_db()
    conn = get_conn()
    existing = conn.execute("SELECT COUNT(*) AS n FROM seed_cases").fetchone()["n"]
    if existing and not force:
        conn.close()
        return existing
    if force:
        conn.execute("DELETE FROM seed_cases")
        conn.commit()
    if SEED_XLSX.exists():
        df = pd.read_excel(SEED_XLSX, sheet_name="病例主表")
    else:
        df = pd.read_csv(SEED_CSV)
    df["doctor_review_label"] = df.get("final_confirmed_diagnosis")
    df["doctor_review_risk"] = df.get("referral_level")
    df["is_training_case"] = df.get("usable_for_quiz").fillna("yes").astype(str).str.lower().isin(["yes", "true", "1", "是"]).astype(int)
    df["review_status"] = "待专家复核"
    cols = [c for c in [
        "case_id","image_id","patient_id_anon","file_name","relative_path","source_batch","original_group","use_tag",
        "disease_level1","disease_level2","working_label","final_confirmed_diagnosis","diagnosis_status","pathology_confirmed",
        "body_site","image_type","image_quality","is_typical_case","danger_signal","referral_level","suspected_diagnosis_1",
        "suspected_diagnosis_2","common_misdiagnosis","symptom_keywords","teaching_point","gold_explanation","usable_for_quiz",
        "village_doctor_level","note","urgency_score","split_suggestion","system_priority","doctor_review_label",
        "doctor_review_risk","is_training_case","review_status"
    ] if c in df.columns]
    df[cols].to_sql("seed_cases", conn, if_exists="append", index=False)
    conn.commit()
    n = conn.execute("SELECT COUNT(*) AS n FROM seed_cases").fetchone()["n"]
    conn.close()
    return n


def upsert_patient(person_id: str, person_name: str, role_bind_hint: str = "", family_contact: str = ""):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO patients(person_id, person_name, role_bind_hint, family_contact) VALUES (?, ?, ?, ?)",
        (person_id, person_name, role_bind_hint, family_contact),
    )
    conn.commit()
    conn.close()


def save_case(case_result: dict):
    conn = get_conn()
    conn.execute(
        '''
        INSERT OR REPLACE INTO cases(
            visit_id, case_id, person_id, person_name, uploader_name, source_role, image_path, body_part,
            duration, itch, pain, bleeding, growth, history, image_quality, quality_ok, quality_message,
            ai_visual_summary, ai_candidates, ai_confidence, risk_level, risk_score, action_advice,
            trend_summary, doctor_review_label, doctor_review_risk, final_outcome, final_diagnosis,
            is_training_case, expert_treatment_plan, expert_followup_plan, expert_reviewer
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            case_result["visit_id"], case_result["case_id"], case_result["person_id"], case_result["person_name"],
            case_result.get("uploader_name"), case_result.get("source_role"), case_result.get("image_path"),
            case_result.get("body_part"), case_result.get("duration"), int(case_result.get("itch", False)),
            int(case_result.get("pain", False)), int(case_result.get("bleeding", False)), int(case_result.get("growth", False)),
            case_result.get("history"), case_result.get("image_quality"), int(case_result.get("quality_ok", True)),
            case_result.get("quality_message"), case_result.get("ai_visual_summary"), case_result.get("ai_candidates"),
            case_result.get("ai_confidence"), case_result.get("risk_level"), case_result.get("risk_score"),
            case_result.get("action_advice"), case_result.get("trend_summary"), case_result.get("doctor_review_label"),
            case_result.get("doctor_review_risk"), case_result.get("final_outcome"), case_result.get("final_diagnosis"),
            int(case_result.get("is_training_case", 0)), case_result.get('expert_treatment_plan'),
            case_result.get('expert_followup_plan'), case_result.get('expert_reviewer'),
        ),
    )
    conn.commit()
    conn.close()


def list_cases(person_name: str | None = None):
    conn = get_conn()
    if person_name:
        rows = conn.execute("SELECT * FROM cases WHERE person_name=? ORDER BY created_at ASC", (person_name,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM cases ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_case_by_visit_id(visit_id: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM cases WHERE visit_id=?", (visit_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_seed_cases(training_only: bool = False):
    conn = get_conn()
    sql = "SELECT * FROM seed_cases"
    if training_only:
        sql += " WHERE is_training_case=1"
    sql += " ORDER BY urgency_score DESC, case_id"
    rows = conn.execute(sql).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_seed_case(case_id: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM seed_cases WHERE case_id=?", (case_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_seed_case_review(case_id: str, label: str, risk: str, teach: bool, status: str):
    conn = get_conn()
    conn.execute(
        "UPDATE seed_cases SET doctor_review_label=?, doctor_review_risk=?, is_training_case=?, review_status=? WHERE case_id=?",
        (label, risk, int(teach), status, case_id),
    )
    conn.commit()
    conn.close()


def add_seed_case(payload: dict):
    conn = get_conn()
    cols = list(payload.keys())
    conn.execute(
        f"INSERT OR REPLACE INTO seed_cases ({','.join(cols)}) VALUES ({','.join(['?']*len(cols))})",
        tuple(payload[c] for c in cols),
    )
    conn.commit()
    conn.close()


def save_audio_note(payload: dict):
    conn = get_conn()
    conn.execute(
        '''
        INSERT OR REPLACE INTO audio_notes(
            note_id, person_id, person_name, visit_id, audio_path, transcript_text, summary_text, structured_json,
            created_by, created_role, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            payload["note_id"], payload.get("person_id"), payload.get("person_name"), payload.get("visit_id"),
            payload.get("audio_path"), payload.get("transcript_text"), payload.get("summary_text"),
            payload.get("structured_json"), payload.get("created_by"), payload.get("created_role"),
            payload.get("status"),
        ),
    )
    conn.commit()
    conn.close()


def list_audio_notes(person_name: str | None = None):
    conn = get_conn()
    if person_name:
        rows = conn.execute("SELECT * FROM audio_notes WHERE person_name=? ORDER BY created_at DESC", (person_name,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM audio_notes ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_training_attempt(payload: dict):
    conn = get_conn()
    conn.execute(
        '''
        INSERT INTO training_attempts(attempt_id, training_type, learner_name, learner_role, question_payload, user_answer, ai_feedback, score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            payload["attempt_id"], payload["training_type"], payload["learner_name"], payload["learner_role"],
            payload["question_payload"], payload["user_answer"], payload["ai_feedback"], payload["score"],
        ),
    )
    conn.commit()
    conn.close()


def list_training_attempts(learner_name: str | None = None):
    conn = get_conn()
    if learner_name:
        rows = conn.execute("SELECT * FROM training_attempts WHERE learner_name=? ORDER BY created_at DESC", (learner_name,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM training_attempts ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def submit_review(payload: dict):
    conn = get_conn()
    conn.execute(
        '''
        INSERT OR REPLACE INTO review_queue(submission_id, source_type, source_id, patient_name, submitted_by, submitted_role, note, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            payload["submission_id"], payload.get("source_type"), payload.get("source_id"), payload.get("patient_name"),
            payload.get("submitted_by"), payload.get("submitted_role"), payload.get("note"), payload.get("status", "待专家复核"),
        ),
    )
    conn.commit()
    conn.close()


def list_review_queue(status: str | None = None):
    conn = get_conn()
    sql = "SELECT * FROM review_queue"
    params = ()
    if status:
        sql += " WHERE status=?"
        params = (status,)
    sql += " ORDER BY created_at DESC"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_review_queue(submission_id: str, status: str):
    conn = get_conn()
    conn.execute("UPDATE review_queue SET status=? WHERE submission_id=?", (status, submission_id))
    conn.commit()
    conn.close()


def apply_expert_review(submission_id: str, status: str, label: str, risk: str, treatment_plan: str, followup_plan: str, review_note: str, reviewer: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM review_queue WHERE submission_id=?", (submission_id,)).fetchone()
    if not row:
        conn.close()
        return False
    row = dict(row)
    conn.execute(
        '''UPDATE review_queue
           SET status=?, final_label=?, final_risk=?, expert_treatment_plan=?, expert_followup_plan=?,
               expert_review_note=?, expert_reviewer=?, expert_reviewed_at=CURRENT_TIMESTAMP
           WHERE submission_id=?''',
        (status, label, risk, treatment_plan, followup_plan, review_note, reviewer, submission_id)
    )
    if row.get('source_type') == 'case_visit' and row.get('source_id'):
        conn.execute(
            '''UPDATE cases
               SET doctor_review_label=?, doctor_review_risk=?, expert_treatment_plan=?, expert_followup_plan=?,
                   expert_reviewer=?, expert_reviewed_at=CURRENT_TIMESTAMP
               WHERE visit_id=?''',
            (label, risk, treatment_plan, followup_plan, reviewer, row['source_id'])
        )
    conn.commit()
    conn.close()
    return True
