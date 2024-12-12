from graphviz import Digraph
import json
from course_scheduler import CourseScheduler

def create_plan_visualization(scheduler, plan):
    # Crear un nuevo grafo
    dot = Digraph(comment='Plan de Estudios')
    dot.attr(rankdir='LR')  # Dirección del grafo de izquierda a derecha
    
    # Configurar estilos
    dot.attr('node', shape='box', style='rounded,filled')
    
    # Colores por término
    term_colors = {
        'C1': '#E6F3FF',  # Azul claro
        'C2': '#FFF0E6'   # Naranja claro
    }
    
    # Agrupar cursos por término
    total_hours = 0
    for term in scheduler.terms:
        courses = plan.get(term, [])
        if courses:
            term_hours = sum(course.hours for course in courses)
            total_hours += term_hours
            
            with dot.subgraph(name=f'cluster_{term}') as s:
                # Agregar el total de horas del término en el título
                s.attr(label=f'Término {term}\n({term_hours} horas)', style='rounded')
                term_color = term_colors['C1'] if term.endswith('C1') else term_colors['C2']
                
                # Agregar cursos del término
                for course in courses:
                    schedule = scheduler.chosen_schedules.get(course.id)
                    if schedule:
                        # Crear label con múltiples líneas
                        label = f"{course.name}\n{course.hours}hs\n"
                        label += f"{', '.join(schedule['days'])}\n{schedule['time']}"
                        s.node(f'course_{course.id}', label, fillcolor=term_color)
                        
                        # Agregar conexiones con correlativas
                        for correlative_id in course.correlatives:
                            dot.edge(f'course_{correlative_id}', f'course_{course.id}')
    
    # Agregar un nodo con el total de horas del plan
    dot.attr('node', shape='note', style='filled', fillcolor='#E6FFE6')  # Verde claro
    dot.node('total_hours', f'Total de horas del plan:\n{total_hours}hs')

    # Guardar el grafo
    dot.render('plan_de_estudios', format='png', cleanup=True)

def create_unassigned_courses_graph(scheduler, plan):
    dot = Digraph(comment='Cursos No Asignados')
    dot.attr(rankdir='LR')
    dot.attr('node', shape='box', style='rounded,filled', fillcolor='#FFE6E6')  # Rojo claro
    
    # Identificar cursos no asignados
    assigned_courses = set()
    total_unassigned_hours = 0
    for courses in plan.values():
        for course in courses:
            assigned_courses.add(course.id)
    
    # Agregar cursos no asignados al grafo
    for course_id, course in scheduler.courses.items():
        if course_id not in assigned_courses:
            total_unassigned_hours += course.hours
            label = f"{course.name}\n{course.hours}hs\n"
            label += "Horarios:\n" + "\n".join(
                f"{', '.join(opt['days'])} {opt['time']}"
                for opt in course.schedule_options
            )
            dot.node(f'course_{course_id}', label)
            
            # Agregar conexiones con correlativas
            for correlative_id in course.correlatives:
                if correlative_id not in assigned_courses:
                    dot.edge(f'course_{correlative_id}', f'course_{course_id}')
    
    # Agregar un nodo con el total de horas no asignadas
    dot.attr('node', shape='note', style='filled', fillcolor='#FFE6E6')
    dot.node('total_unassigned_hours', f'Total de horas no asignadas:\n{total_unassigned_hours}hs')

    # Guardar el grafo
    dot.render('cursos_no_asignados', format='png', cleanup=True)

if __name__ == "__main__":
    # Crear el planificador y generar el plan
    scheduler = CourseScheduler("mecatronica-2024C2.json", {
        'preferred_time': 'day',
        'max_hours_per_term': 800
    }, "user_config.json")
    
    plan = scheduler.plan_courses()
    
    # Generar visualizaciones
    create_plan_visualization(scheduler, plan)
    create_unassigned_courses_graph(scheduler, plan)
    
    # Calcular totales
    total_assigned_hours = sum(
        course.hours
        for courses in plan.values()
        for course in courses
    )
    
    total_unassigned_hours = sum(
        course.hours
        for course in scheduler.courses.values()
        if not any(course in term_courses for term_courses in plan.values())
    )
    
    print("\nVisualizaciones generadas:")
    print("- plan_de_estudios.png: Muestra el plan de estudios asignado")
    print("- cursos_no_asignados.png: Muestra los cursos que no se pudieron asignar")
    print(f"\nResumen de horas:")
    print(f"- Horas asignadas: {total_assigned_hours}")
    print(f"- Horas no asignadas: {total_unassigned_hours}")
    print(f"- Total de horas de la carrera: {total_assigned_hours + total_unassigned_hours}") 