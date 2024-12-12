from collections import defaultdict, deque
import json

class Course:
    def __init__(self, id, name, year, term, hours, schedule_options, correlatives):
        self.id = id
        self.name = name
        self.year = year
        self.term = term
        self.hours = hours
        self.schedule_options = schedule_options
        self.correlatives = correlatives

class CourseScheduler:
    def __init__(self, courses_json_path, preferences=None, config_json_path=None):
        if preferences is None:
            preferences = {'preferred_time': 'day', 'max_hours_per_term': 384}
        
        self.preferences = preferences
        self.terms = [
            '2025C1', '2025C2', '2026C1', '2026C2', '2027C1', '2027C2',
            '2028C1', '2028C2', '2029C1', '2029C2', '2030C1', '2030C2',
            '2031C1', '2031C2', '2032C1', '2032C2', '2033C1', '2033C2',
            '2034C1', '2034C2', '2035C1', '2035C2', '2036C1', '2036C2',
            '2037C1', '2037C2', '2038C1', '2038C2', '2039C1', '2039C2',
            '2040C1', '2040C2'
        ]
        
        # Cargar cursos desde JSON
        with open(courses_json_path, 'r', encoding='utf-8') as file:
            courses_data = json.load(file)
            self.courses = {
                c['id']: Course(
                    c['id'], c['name'], c['year'], c['term'],
                    c['hours'], c['scheduleOptions'], c['correlatives']
                ) for c in courses_data
            }
        
        # Cargar configuración del usuario si existe
        self.approved_courses = set()
        if config_json_path:
            self._load_user_config(config_json_path)

    def _load_user_config(self, config_path):
        """Carga la configuración del usuario desde un archivo JSON."""
        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                config = json.load(file)
                self.approved_courses = set(config.get('approved_courses', []))
                
                # Validar que los IDs existan en los cursos
                invalid_courses = self.approved_courses - set(self.courses.keys())
                if invalid_courses:
                    print(f"Advertencia: Los siguientes IDs de cursos aprobados no existen: {invalid_courses}")
                    self.approved_courses -= invalid_courses
                
                print(f"\nCursos aprobados cargados: {len(self.approved_courses)}")
                for course_id in self.approved_courses:
                    print(f"- {self.courses[course_id].name}")
                
        except FileNotFoundError:
            print(f"Advertencia: No se encontró el archivo de configuración en {config_path}")
        except json.JSONDecodeError:
            print(f"Error: El archivo de configuración en {config_path} no es un JSON válido")
        except Exception as e:
            print(f"Error al cargar la configuración: {str(e)}")

    def _build_graph(self):
        """Construye el grafo de dependencias y su inverso."""
        graph = defaultdict(list)
        inverse_graph = defaultdict(list)
        in_degree = defaultdict(int)
        
        for course_id, course in self.courses.items():
            if not course.correlatives:
                in_degree[course_id] = 0
            for correlative_id in course.correlatives:
                graph[correlative_id].append(course_id)
                inverse_graph[course_id].append(correlative_id)
                in_degree[course_id] += 1
        
        return graph, inverse_graph, in_degree

    def _topological_sort(self):
        """Realiza el ordenamiento topológico de los cursos."""
        graph, inverse_graph, in_degree = self._build_graph()
        
        # Cola para cursos sin dependencias
        queue = deque([
            course_id for course_id, degree in in_degree.items()
            if degree == 0
        ])
        
        sorted_courses = []
        levels = defaultdict(list)  # Para agrupar cursos por nivel de dependencia
        course_levels = {}  # Para guardar el nivel de cada curso
        current_level = 0
        
        while queue:
            level_size = len(queue)
            for _ in range(level_size):
                course_id = queue.popleft()
                sorted_courses.append(course_id)
                levels[current_level].append(course_id)
                course_levels[course_id] = current_level
                
                # Procesar los cursos que dependen de este
                for dependent in graph[course_id]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)
            
            current_level += 1
        
        return sorted_courses, levels, course_levels

    def _check_schedule_compatibility(self, schedule1, schedule2):
        """Verifica si dos horarios son compatibles."""
        days1 = set(schedule1['days'])
        days2 = set(schedule2['days'])
        
        # Si no comparten días, son compatibles
        if not (days1 & days2):
            return True
            
        # Convertir horarios a minutos
        start1, end1 = map(lambda x: int(x.split(':')[0]) * 60 + int(x.split(':')[1]),
                          schedule1['time'].split('-'))
        start2, end2 = map(lambda x: int(x.split(':')[0]) * 60 + int(x.split(':')[1]),
                          schedule2['time'].split('-'))
        
        # Verificar superposición
        return end1 <= start2 or end2 <= start1

    def _find_valid_schedule(self, course, term_courses):
        """Encuentra un horario válido para el curso que no se superponga con los existentes."""
        for new_schedule in course.schedule_options:
            valid = True
            for existing_course in term_courses:
                if existing_course.id in self.chosen_schedules:
                    existing_schedule = self.chosen_schedules[existing_course.id]
                    if not self._check_schedule_compatibility(new_schedule, existing_schedule):
                        valid = False
                        break
            if valid:
                return new_schedule
        return None

    def _can_assign_to_term(self, course, term, current_plan):
        """Verifica si un curso puede ser asignado a un término específico."""
        # Si el curso está aprobado, no se puede asignar
        if course.id in self.approved_courses:
            return False

        # Verificar correlativas
        for correlative_id in course.correlatives:
            # Si la correlativa está aprobada, la consideramos completada
            if correlative_id in self.approved_courses:
                continue
                
            correlative_completed = False
            for prev_term in self.terms[:self.terms.index(term)]:
                if any(c.id == correlative_id for c in current_plan.get(prev_term, [])):
                    correlative_completed = True
                    break
            if not correlative_completed:
                return False

        # Verificar límite de horas
        term_courses = current_plan.get(term, [])
        if sum(c.hours for c in term_courses) + course.hours > self.preferences['max_hours_per_term']:
            return False

        # Verificar disponibilidad de horario
        return self._find_valid_schedule(course, term_courses) is not None

    def _try_schedule_courses(self, remaining_courses, current_plan, attempted=None):
        """Intenta programar los cursos restantes usando backtracking."""
        if attempted is None:
            attempted = set()

        # Si no hay más cursos para asignar, retornamos el plan actual
        if not remaining_courses:
            return True, current_plan

        course_id = remaining_courses[0]
        course = self.courses[course_id]
        
        # Si el curso está aprobado, pasamos al siguiente
        if course_id in self.approved_courses:
            return self._try_schedule_courses(remaining_courses[1:], current_plan, attempted)
        
        # Evitar ciclos infinitos
        assignment_key = f"{course_id}"
        if assignment_key in attempted:
            return self._try_schedule_courses(remaining_courses[1:], current_plan, set())

        # Intentar asignar el curso en cada término posible
        for term in self.terms:
            test_plan = {t: courses[:] for t, courses in current_plan.items()}
            
            if self._can_assign_to_term(course, term, test_plan):
                test_plan[term].append(course)
                schedule = self._find_valid_schedule(course, test_plan[term][:-1])
                self.chosen_schedules[course_id] = schedule
                
                success, new_plan = self._try_schedule_courses(
                    remaining_courses[1:],
                    test_plan,
                    attempted
                )
                
                if success:
                    return True, new_plan

        attempted.add(assignment_key)
        return self._try_schedule_courses(remaining_courses[1:], current_plan, set())

    def plan_courses(self):
        """Genera un plan de estudios completo."""
        # Inicializar estructuras
        self.chosen_schedules = {}
        initial_plan = {term: [] for term in self.terms}
        
        # Obtener orden topológico de los cursos
        sorted_courses, levels, course_levels = self._topological_sort()
        
        # Filtrar los cursos aprobados
        courses_to_schedule = [
            course_id for course_id in sorted_courses 
            if course_id not in self.approved_courses
        ]
        
        # Intentar generar el plan
        success, final_plan = self._try_schedule_courses(courses_to_schedule, initial_plan)
        
        # Identificar cursos asignados y no asignados
        assigned_courses = set()
        for courses in final_plan.values():
            for course in courses:
                assigned_courses.add(course.id)
        
        unassigned_courses = []
        for course_id in courses_to_schedule:  # Solo verificar cursos no aprobados
            if course_id not in assigned_courses:
                course = self.courses[course_id]
                unassigned_courses.append(course)
        
        if unassigned_courses:
            print("\nNo se pudo generar un plan completo.")
            print("\nCursos no asignados:")
            for course in unassigned_courses:
                print(f"\n{course.name} (ID: {course.id})")
                print(f"Correlativas: {course.correlatives}")
                print("Horarios disponibles:")
                for schedule in course.schedule_options:
                    print(f"  {', '.join(schedule['days'])} {schedule['time']}")
        
        if not any(courses for courses in final_plan.values()):
            print("\nError: No se pudo asignar ningún curso.")
        
        return final_plan

if __name__ == "__main__":
    scheduler = CourseScheduler(
        courses_json_path="mecatronica-2024C2.json",
        preferences={'preferred_time': 'day', 'max_hours_per_term': 384},
        config_json_path="user_config.json"
    )
    
    plan = scheduler.plan_courses()
    
    # Imprimir el plan resultante
    print("\nPlan de estudios:")
    for term, courses in plan.items():
        if courses:
            print(f"\nTérmino {term}:")
            term_hours = sum(course.hours for course in courses)
            for course in courses:
                schedule = scheduler.chosen_schedules.get(course.id)
                if schedule:
                    days = ", ".join(schedule['days'])
                    print(f"- {course.name} ({course.hours} horas)")
                    print(f"  Horario: {days} {schedule['time']}")
            print(f"Total de horas del término: {term_hours}")
