import random
from services.db_service import list_seed_cases


def filter_training_cases(disease: str = '全部', level: str = '全部', question_type: str = '全部'):
    cases = list_seed_cases(training_only=True)
    out = []
    for c in cases:
        if disease != '全部' and c.get('final_confirmed_diagnosis') != disease and c.get('working_label') != disease:
            continue
        if level != '全部' and str(c.get('village_doctor_level')) != str(level):
            continue
        if question_type != '全部' and question_type not in str(c.get('use_tag', '')):
            continue
        out.append(c)
    return out


def pick_case(disease='全部', level='全部', question_type='全部'):
    cases = filter_training_cases(disease, level, question_type)
    return random.choice(cases) if cases else None


def pick_dual_cases(disease='全部'):
    cases = filter_training_cases(disease=disease)
    if len(cases) < 2:
        cases = list_seed_cases(training_only=True)
    if len(cases) < 2:
        return []
    return random.sample(cases, 2)
