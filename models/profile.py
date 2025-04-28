class Profile:
    def __init__(self, name, appearance, background, personality, attitude, goal, benefit, special,
                 influence_successes, successes_needed, biases, strengths, weaknesses, influence_skills, photoUrl):
        self.name = name
        self.appearance = appearance
        self.background = background
        self.personality = personality
        self.attitude = attitude
        self.goal = goal
        self.benefit = benefit
        self.special = special
        self.influence_successes = influence_successes
        self.successes_needed = successes_needed
        self.biases = biases  # List of dicts: {'text': ..., 'revealed': bool}
        self.strengths = strengths
        self.weaknesses = weaknesses
        self.influence_skills = influence_skills
        self.photoUrl = photoUrl

    def to_dict(self):
        return self.__dict__

    def to_player_dict(self):
        """ Only show revealed info for players """
        return {
            **{k: v for k, v in self.__dict__.items() if k not in ['biases', 'strengths', 'weaknesses', 'influence_skills']},
            'biases': [b['text'] for b in self.biases if b['revealed']],
            'strengths': [s['text'] for s in self.strengths if s['revealed']],
            'weaknesses': [w['text'] for w in self.weaknesses if w['revealed']],
            'influence_skills': [i['text'] for i in self.influence_skills if i['revealed']]
        }

    @staticmethod
    def from_dict(data):
        def ensure_list_of_dicts(lst):
            if not lst:
                return []
            # If it's a list of strings (not dicts), convert them
            if isinstance(lst[0], str):
                return [{'text': item, 'revealed': True} for item in lst]
            return lst

        return Profile(
            name=data.get('name', ''),
            appearance=data.get('appearance', ''),
            background=data.get('background', ''),
            personality=data.get('personality', ''),
            attitude=data.get('attitude', ''),
            goal=data.get('goal', ''),
            benefit=data.get('benefit', ''),
            special=data.get('special', ''),
            influence_successes=data.get('influence_successes', 0),
            successes_needed=data.get('successes_needed', 0),
            biases=ensure_list_of_dicts(data.get('biases', [])),
            strengths=ensure_list_of_dicts(data.get('strengths', [])),
            weaknesses=ensure_list_of_dicts(data.get('weaknesses', [])),
            influence_skills=ensure_list_of_dicts(data.get('influence_skills', [])),
            photoUrl=data.get('photoUrl', '')
        )

