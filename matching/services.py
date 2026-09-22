import re
from typing import Dict, Any, List, Optional

# Configurable matching weights (Section 9)
MATCH_WEIGHTS = {
    'title': 30,
    'skills': 40,
    'location': 10,
    'work_mode': 10,
    'experience': 10,
}

def calculate_match_score(job, profile, default_resume=None) -> Dict[str, Any]:
    """
    Deterministic, explainable matching engine comparing a Job against a User's Profile & Resume.
    
    Weights (Configurable):
    - Title match: 30 pts
    - Skills match: 40 pts
    - Location match: 10 pts
    - Work mode match: 10 pts
    - Experience match: 10 pts
    Total: 100 pts

    Returns:
    {
        "score": 82,
        "reasons": [
            "Python matches target skills",
            "SQL matches target skills",
            "Bengaluru matches preferred location"
        ],
        "missing_skills": [
            "Airflow"
        ],
        "breakdown": { ... }
    }
    """
    if not profile:
        return {
            'score': 0,
            'total_score': 0,
            'reasons': ["No profile configured"],
            'missing_skills': job.skills_list,
            'matched_skills': [],
            'breakdown': {},
            'role': {'score': 0, 'max_score': MATCH_WEIGHTS['title'], 'details': 'No profile configured', 'matched': []},
            'skills': {'score': 0, 'max_score': MATCH_WEIGHTS['skills'], 'matched': [], 'missing': job.skills_list, 'details': 'No profile configured'},
            'location': {'score': 0, 'max_score': MATCH_WEIGHTS['location'], 'details': 'No profile configured'},
            'work_mode': {'score': 0, 'max_score': MATCH_WEIGHTS['work_mode'], 'details': 'No profile configured'},
            'experience': {'score': 0, 'max_score': MATCH_WEIGHTS['experience'], 'details': 'No profile configured'},
            'salary': {'score': 0, 'max_score': 10, 'details': 'No profile configured'},
        }

    reasons: List[str] = []
    missing_skills: List[str] = []
    matched_skills: List[str] = []

    # 1. Title Match (30 pts)
    title_max = MATCH_WEIGHTS['title']
    title_score = 0
    title_details = "Job title does not match preferred titles"
    matched_roles = []
    job_title_lower = (job.title or '').lower()
    preferred_titles = profile.preferred_job_titles_list

    if preferred_titles:
        for p_title in preferred_titles:
            p_words = set(re.findall(r'\w+', p_title.lower()))
            j_words = set(re.findall(r'\w+', job_title_lower))
            overlap = p_words.intersection(j_words)
            if p_title.lower() in job_title_lower or (overlap and len(overlap) >= max(1, len(p_words) * 0.5)):
                matched_roles.append(p_title)

        if matched_roles:
            title_score = title_max
            title_details = f"Direct match with target titles: {', '.join(matched_roles)}"
            reasons.append(f"Title matches your preferred role '{matched_roles[0]}'")
        else:
            all_target_tokens = set(re.findall(r'\w+', profile.preferred_job_titles.lower()))
            common_tokens = all_target_tokens.intersection(set(re.findall(r'\w+', job_title_lower)))
            if common_tokens:
                title_score = int(title_max * 0.5)
                title_details = f"Partial title match on keywords: {', '.join(common_tokens)}"
                reasons.append(f"Role title partially matches target keywords ({', '.join(common_tokens)})")
            else:
                title_score = 0
    else:
        title_score = int(title_max * 0.5)
        title_details = "No target roles configured (baseline applied)"

    # 2. Skills Match (40 pts)
    skills_max = MATCH_WEIGHTS['skills']
    profile_skills = set(s.lower().strip() for s in profile.skills_list if s.strip())
    resume_skills = set(s.lower().strip() for s in (default_resume.detected_skills if default_resume else []))
    all_user_skills = profile_skills.union(resume_skills)

    job_skills = [s.strip() for s in job.skills_list if s.strip()]
    
    # Fallback to scanning description if explicit skills field is empty
    if not job_skills and job.description:
        desc_lower = job.description.lower()
        for us in all_user_skills:
            if re.search(r'\b' + re.escape(us) + r'\b', desc_lower):
                job_skills.append(us.title())

    if job_skills:
        for js in job_skills:
            js_lower = js.lower()
            if js_lower in all_user_skills or any(us in js_lower or js_lower in us for us in all_user_skills):
                matched_skills.append(js)
                reasons.append(f"{js} matches target skills")
            else:
                missing_skills.append(js)

        ratio = len(matched_skills) / len(job_skills)
        skill_score = int(round(ratio * skills_max))
        skill_details = f"Matched {len(matched_skills)} of {len(job_skills)} required skills ({round(ratio * 100)}%)"
    else:
        skill_score = int(skills_max * 0.6)
        skill_details = "No specific skills listed for job (baseline score)"

    # 3. Location Match (10 pts)
    loc_max = MATCH_WEIGHTS['location']
    loc_score = 0
    job_loc_lower = (job.location or '').lower()
    pref_locs = [l.lower().strip() for l in profile.preferred_locations_list if l.strip()]
    curr_loc = (profile.current_location or '').lower().strip()

    if job.work_mode in ('REMOTE', 'Remote') or 'remote' in job_loc_lower:
        loc_score = loc_max
        loc_details = "Fully remote position - perfect location fit"
        reasons.append("Remote position allows working from anywhere")
    elif any(pref in job_loc_lower for pref in pref_locs if pref):
        loc_score = loc_max
        matched_loc = next(pref for pref in pref_locs if pref in job_loc_lower)
        loc_details = f"Job is located in your preferred location ({job.location})"
        reasons.append(f"{job.location} matches preferred location")
    elif curr_loc and curr_loc in job_loc_lower:
        loc_score = loc_max
        loc_details = f"Job is located in your current city ({job.location})"
        reasons.append(f"{job.location} matches your current location")
    elif not pref_locs:
        loc_score = int(loc_max * 0.6)
        loc_details = "No preferred location specified (neutral score)"
    else:
        loc_score = 0
        loc_details = f"Job location ({job.location}) does not match preferred locations"

    # 4. Work Mode Match (10 pts)
    mode_max = MATCH_WEIGHTS['work_mode']
    mode_score = 0
    user_pref = profile.work_preference

    if user_pref == 'FLEXIBLE':
        mode_score = mode_max
        mode_details = f"Flexible work preference matches {job.get_work_mode_display()}"
        reasons.append(f"Flexible preference fits {job.get_work_mode_display()} mode")
    elif user_pref == job.work_mode:
        mode_score = mode_max
        mode_details = f"Exact match for preferred work mode: {job.get_work_mode_display()}"
        reasons.append(f"{job.get_work_mode_display()} matches your preferred work mode")
    elif user_pref == 'HYBRID' and job.work_mode in ('REMOTE', 'HYBRID'):
        mode_score = int(mode_max * 0.8)
        mode_details = f"Compatible hybrid/remote policy ({job.get_work_mode_display()})"
        reasons.append(f"{job.get_work_mode_display()} work mode is compatible with Hybrid")
    elif user_pref == 'REMOTE' and job.work_mode != 'REMOTE':
        mode_score = 0
        mode_details = f"Requires {job.get_work_mode_display()} while you prefer Remote"
    else:
        mode_score = int(mode_max * 0.5)
        mode_details = f"Work style is {job.get_work_mode_display()}"

    # 5. Experience Match (10 pts)
    exp_max = MATCH_WEIGHTS['experience']
    exp_score = 0
    user_exp = float(profile.years_of_experience or 0.0)
    req_exp_min = float(job.experience_min or 0.0)
    req_exp_max = float(job.experience_max or 0.0) if job.experience_max else None

    if req_exp_min == 0.0 or user_exp >= req_exp_min:
        exp_score = exp_max
        exp_details = f"Your experience ({user_exp:g} yrs) meets or exceeds requirement ({req_exp_min:g} yrs)"
        reasons.append(f"{user_exp:g} yrs experience meets requirement ({req_exp_min:g}+ yrs)")
    elif user_exp >= (req_exp_min - 1.0):
        exp_score = int(exp_max * 0.7)
        exp_details = f"Your experience ({user_exp:g} yrs) is close to the requirement ({req_exp_min:g} yrs)"
        reasons.append(f"{user_exp:g} yrs experience is close to {req_exp_min:g} yrs requirement")
    else:
        exp_score = int(exp_max * 0.2)
        exp_details = f"Requires {req_exp_min:g} yrs experience (you have {user_exp:g} yrs)"

    # Total Score Calculation
    total_score = title_score + skill_score + loc_score + mode_score + exp_score
    total_score = max(0, min(100, int(round(total_score))))

    breakdown = {
        'title': {'score': title_score, 'max': title_max, 'details': title_details},
        'skills': {'score': skill_score, 'max': skills_max, 'details': skill_details, 'matched': matched_skills, 'missing': missing_skills},
        'location': {'score': loc_score, 'max': loc_max, 'details': loc_details},
        'work_mode': {'score': mode_score, 'max': mode_max, 'details': mode_details},
        'experience': {'score': exp_score, 'max': exp_max, 'details': exp_details},
    }

    return {
        'score': total_score,
        'total_score': total_score,  # Alias for backward compatibility
        'reasons': reasons,
        'missing_skills': missing_skills,
        'matched_skills': matched_skills,
        'breakdown': breakdown,
        # Legacy template compatibility keys
        'role': {'score': title_score, 'max_score': title_max, 'details': title_details, 'matched': matched_roles},
        'skills_score_info': {'score': skill_score, 'max_score': skills_max, 'matched': matched_skills, 'missing': missing_skills, 'details': skill_details},
        'location': {'score': loc_score, 'max_score': loc_max, 'details': loc_details},
        'work_mode': {'score': mode_score, 'max_score': mode_max, 'details': mode_details},
        'experience': {'score': exp_score, 'max_score': exp_max, 'details': exp_details},
        'salary': {'score': 10, 'max_score': 10, 'details': job.formatted_salary},
    }
