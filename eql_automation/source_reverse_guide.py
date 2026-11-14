"""Reverse retained itinerary geometry into hints for a new checked journey.

Old floor proofs are provenance only. The returned guide must be rebuilt from
the caller's actual current floor; it cannot commit the retained destination.
"""
from .source_itinerary import SourceItineraryGuide,SourceItineraryPlan,SourceWalkHint,SourceStepHint,xy


def reverse_source_plan(plan,*,first_cell=0,goal=None):
    if type(plan) is not SourceItineraryPlan:
        raise ValueError('Pinned source itinerary evidence required')
    data=plan.record();cells=data['cells']
    if (type(first_cell) is not int or not 0<=first_cell<len(cells)
            or len(cells)>10000 or data.get('geometry_candidate') is not True):
        raise ValueError('Bounded retained itinerary suffix required')
    point=tuple(data['goal']);operations=[]
    for cell in reversed(cells[first_cell:]):
        start,end=tuple(cell['end']),tuple(cell['start'])
        if not xy(start) or not xy(end) or start!=point:
            raise ValueError('Retained itinerary has an unexplained gap')
        if cell['kind']=='walk':
            operations.append(SourceWalkHint(start,end))
        elif cell['kind']=='step':
            transfer=cell['transfer'];e=transfer['evidence']
            if (transfer['candidate'] is not True or tuple(e['start'])!=end
                    or tuple(e['end'])!=start or e['source_wld_sha256']!=data['source_wld_sha256']
                    or e['static_inventory_sha256']!=data['static_inventory_sha256']
                    or e['radius']!=data['radius'] or e['body_height']!=data['body_height']):
                raise ValueError('Retained step differs from its itinerary')
            operations.append(SourceStepHint(start,end,
                tuple(tuple(k) for k in e['lower_endpoint']['selected_ids']),
                e['max_step_height'],e['max_lift'],e['lift_clearance']))
        else:raise ValueError('Unknown retained itinerary cell')
        point=end
    guide=SourceItineraryGuide(data['zone'],data['source_wld_sha256'],
        data['static_inventory_sha256'],plan.sha256,data['radius'],data['body_height'],
        point if goal is None else goal,tuple(operations))
    guide.validate();return guide
