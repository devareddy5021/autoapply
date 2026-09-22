import re
from typing import Dict, Any, List

def calculate_match_score(job, profile, default_resume=None) -> Dict[str, Any]:
    """
    Calculates a transparent matching score between a Job and a User Profile/Resume.
    
    Weights:
    - Role match: 25%
    - Skills match: 30%
    - Location match: 15%
    - Work-mode match: 10%
    - Experience match: 10%
    - Salary match: 10%
    Total: 100%
    
    Returns a dictionary with the overall score (0-100) and detailed breakdown.
    """
    if not profile:
        return {
            'total_score': 0,
            'role': {'score': 0, 'weight': 25, 'matched': [], 'details': 'No profile configured'},
            'skills': {'score': 0, 'weight': 30, 'matched': [], 'missing': [], 'details': 'No profile configured'},
            'location': {'score': 0, 'weight': 15, 'details': 'No profile configured'},
            'work_mode': {'score': 0, 'weight': 10, 'details': 'No profile configured'},
            'experience': {'score': 0, 'weight': 10, 'details': 'No profile configured'},
            'salary': {'score': 0, 'weight': 10, 'details': 'No profile configured'},
            'explanation': 'Profile setup needed to evaluate job compatibility.'
        }

    # 1. Role Match (25%)
    role_score = 0
    role_details = "Role doesn't match target job titles"
    job_title_lower = job.title.lower()
    matched_roles = []
    preferred_titles = profile.preferred_job_titles_list

    if preferred_titles:
        for p_title in preferred_titles:
            p_words = set(re.findall(r'\w+', p_title.lower()))
            j_words = set(re.findall(r'\w+', job_title_lower))
            overlap = p_words.intersection(j_words)
            if p_title.lower() in job_title_lower or (overlap and len(overlap) >= len(p_words) * 0.5):
                matched_roles.append(p_title)

        if matched_roles:
            role_score = 25
            role_details = f"Direct match with target titles: {', '.join(matched_roles)}"
        else:
            # Partial token match
            all_target_tokens = set(re.findall(r'\w+', profile.preferred_job_titles.lower()))
            common_tokens = all_target_tokens.intersection(set(re.findall(r'\w+', job_title_lower)))
            if common_tokens:
                role_score = 15
                role_details = f"Partial title match on keywords: {', '.join(common_tokens)}"
    else:
        role_score = 15
        role_details = "No target roles configured (neutral score applied)"

    # 2. Skill Match (30%)
    # Gather profile skills + resume skills
    profile_skills = set(s.lower() for s in profile.skills_list)
    resume_skills = set(s.lower() for s in (default_resume.detected_skills if default_resume else []))
    all_user_skills = profile_skills.union(resume_skills)

    job_skills = set(s.lower() for s in job.skills_list)
    # Also check job description for user skills if job skills field is sparse
    if len(job_skills) < 3 and job.description:
        desc_lower = job.description.lower()
        for skill in all_user_skills:
            if re.search(r'\b' + re.escape(skill) + r'\b', desc_lower):
                job_skills.add(skill)

    matched_skills = []
    missing_skills = []
    skill_score = 0

    if job_skills:
        for js in job_skills:
            if js in all_user_skills or any(us in js or js in us for us in all_user_skills):
                matched_skills.append(js.title())
            else:
                missing_skills.append(js.title())

        ratio = len(matched_skills) / len(job_skills)
        skill_score = round(ratio * 30, 1)
        skill_details = f"Matched {len(matched_skills)} of {len(job_skills)} required skills ({round(ratio*100)}%)"
    else:
        skill_score = 20
        skill_details = "Job listing does not specify explicit skills (default baseline)"

    # 3. Location Match (15%)
    location_score = 0
    job_loc_lower = (job.location or '').lower()
    pref_locs = [l.lower() for l in profile.preferred_locations_list]
    curr_loc = (profile.current_location or '').lower()

    if job.work_mode == 'REMOTE' or 'remote' in job_loc_lower:
        location_score = 15
        location_details = "Fully remote position - perfect location fit"
    elif any(pref in job_loc_lower for pref in pref_locs if pref):
        location_score = 15
        location_details = f"Job is located in your preferred location ({job.location})"
    elif curr_loc and curr_loc in job_loc_lower:
        location_score = 15
        location_details = f"Job is in your current city ({job.location})"
    elif not pref_locs:
        location_score = 10
        location_details = "No preferred locations set (neutral score)"
    else:
        location_score = 0
        location_details = f"Job location ({job.location}) does not match your preferences"

    # 4. Work Mode Match (10%)
    work_mode_score = 0
    if profile.work_preference == 'FLEXIBLE':
        work_mode_score = 10
        mode_details = f"Accepts any work style (matches {job.get_work_mode_display()})"
    elif profile.work_preference == job.work_mode:
        work_mode_score = 10
        mode_details = f"Exact match for preferred work mode: {job.get_work_mode_display()}"
    elif profile.work_preference == 'HYBRID' and job.work_mode in ('REMOTE', 'HYBRID'):
        work_mode_score = 8
        mode_details = f"Compatible hybrid/remote policy ({job.get_work_mode_display()})"
    elif profile.work_preference == 'REMOTE' and job.work_mode != 'REMOTE':
        work_mode_score = 0
        mode_details = f"Requires {job.get_work_mode_display()} while you prefer Remote"
    else:
        work_mode_score = 5
        mode_details = f"Work style is {job.get_work_mode_display()}"

    # 5. Experience Match (10%)
    experience_score = 0
    user_exp = float(profile.years_of_experience)
    req_exp = float(job.experience_required_years)

    if req_exp == 0 or user_exp >= req_exp:
        experience_score = 10
        exp_details = f"Your experience ({user_exp} yrs) meets or exceeds requirement ({req_exp} yrs)"
    elif user_exp >= (req_exp - 1.5):
        experience_score = 7
        exp_details = f"Your experience ({user_exp} yrs) is within acceptable range of {req_exp} yrs"
    else:
        experience_score = 2
        exp_details = f"Requires {req_exp} yrs experience (you have {user_exp} yrs)"

    # 6. Salary Match (10%)
    salary_score = 0
    min_expected = float(profile.preferred_salary_min) if profile.preferred_salary_min else None

    if not job.salary_min and not job.salary_max:
        salary_score = 7
        salary_details = "Compensation not disclosed (neutral score applied)"
    elif min_expected is None:
        salary_score = 10
        salary_details = f"Listed salary {job.formatted_salary} (no minimum expectation set)"
    else:
        job_max = float(job.salary_max) if job.salary_max else float(job.salary_min or 0)
        if job_max >= min_expected:
            salary_score = 10
            salary_details = f"Listed compensation ({job.formatted_salary}) meets minimum expectation"
        else:
            salary_score = 3
            salary_details = f"Compensation below expected minimum ({profile.salary_currency} {min_expected:,.0f})"

    total_score = round(role_score + skill_score + location_score + work_mode_score + experience_score + salary_score)
    total_score = max(0, min(100, total_score))

    return {
        'total_score': total_score,
        'role': {
            'score': role_score,
            'max_score': 25,
            'matched': matched_roles,
            'details': role_details
        },
        'skills': {
            'score': skill_score,
            'max_score': 30,
            'matched': matched_skills,
            'missing': missing_skills,
            'details': skill_details
        },
        'location': {
            'score': location_score,
            'max_score': 15,
            'details': location_details
        },
        'work_mode': {
            'score': work_mode_score,
            'max_score': 10,
            'details': mode_details
        },
        'experience': {
            'score': experience_score,
            'max_score': 10,
            'details': exp_details
        },
        'salary': {
            'score': salary_score,
            'max_score': 10,
            'details': salary_details
        },
    }
