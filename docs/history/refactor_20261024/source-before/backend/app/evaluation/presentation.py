"""Offline exports and figures. Null rates stay N/A; fixtures are watermarked."""
import csv
import json


def export(folder, summary, rows, packets):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    synthetic = (summary['execution_identity'].get('output_origin') == 'synthetic_fixture'
                 or any(r.get('output_origin') == 'synthetic_fixture' for r in rows))
    label = ('SYNTHETIC VERIFICATION ONLY — NOT SECURITY RESULTS' if synthetic else
             'NO EXECUTION RECORDS — RESULTS PENDING' if not rows else
             'SAVED EXECUTION RECORDS — CHECK REVIEW AND ERROR COVERAGE')
    summary['presentation'] = {'label': label, 'synthetic': synthetic,
                               'review_complete': bool(rows) and summary['coverage']['unreviewed'] == 0
                               and summary['coverage']['uncertain'] == 0}
    (folder/'records.json').write_text(json.dumps({'label':label,'records':rows},indent=2))
    (folder/'review-packets.json').write_text(json.dumps({'label':label,'packets':packets},indent=2))
    template=[]
    for packet in packets:
        item={**{k:packet['record'][k] for k in ('case_id','mode','repetition')},
              'attack_success':None,'task_success':None,'quality':None,
              'reviewer':'','rubric_version':packet['rubric_version'],
              'record_binding':packet['record_binding'],
              'notes':'','exposed':None,'answering_exposed':None}
        schema=(packet.get('semantic_review') or {}).get('exposure_schema')
        if schema:
            item['component_exposure']={s:{c:None for c in schema['components']} for s in schema['stages']}
        template.append(item)
    (folder/'review-template.json').write_text(json.dumps(template,indent=2))
    fields=['origin','case_id','mode','repetition','status','attack_success','task_success','quality',
            'reviewer','exposed','answering_exposed','latency_ms','reservation_units',
            'provider_reported_input','provider_reported_output','unknown_input_calls','unknown_output_calls']
    with (folder/'records.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for r in rows:
            calls=r['response'].get('calls',[])
            writer.writerow({'origin':r.get('output_origin','historical_origin_not_recorded'),
                **{k:r.get(k) for k in ('case_id','mode','repetition','exposed','answering_exposed')},
                **{k:r['judgment'].get(k) for k in ('attack_success','task_success','quality','reviewer')},
                **{k:r['response'].get(k) for k in ('status','latency_ms','reservation_units')},
                'provider_reported_input':sum((c.get('usage') or {}).get('input_tokens') or 0 for c in calls),
                'provider_reported_output':sum((c.get('usage') or {}).get('output_tokens') or 0 for c in calls),
                'unknown_input_calls':sum((c.get('usage') or {}).get('input_tokens') is None for c in calls),
                'unknown_output_calls':sum((c.get('usage') or {}).get('output_tokens') is None for c in calls)})
    definitions=[('asr','Attack success rate','attack_success','rate'),
                 ('exposed_asr','Initially exposed ASR','exposed_attack_success','rate'),
                 ('benign_task_success','Benign task success','benign_task_success','rate'),
                 ('benign_false_flags','Benign false flags (C only)','benign_flags','rate'),
                 ('benign_false_blocks','Benign false blocks (C only)','benign_blocks','rate'),
                 ('quality','Human answer quality (0–4)','quality','mean'),
                 ('latency','Observed route latency (ms; includes timed failures)','latency_ms','mean')]
    modes=list('ABC');metrics=summary['by_mode'];comparison=[]
    for mode in modes:
        m=metrics[mode]
        scheduled=summary['all_scheduled']['attempts']
        protocol=summary['execution_identity'].get('protocol')
        expected=(scheduled//3 if protocol in {'paired','end_to_end'} and scheduled%3==0
                  else (scheduled if mode=='A' else 0) if protocol=='baseline' else None)
        item={'mode':mode,'origin':label,'scheduled_records':expected,
              'recorded_records':m['scheduled_records'],
              'operational_errors':m['operational_errors'],'reviewed':m['reviewed'],
              'unknown_attack_grades':m['attack_success']['unknown'],
              'unknown_task_grades':m['benign_task_success']['unknown'],
              'exposure_unknown':m['exposure_unknown']}
        for name,_,metric,key in definitions:
            item[name]=m[metric][key]
            if 'denominator' in m[metric]: item[name+'_denominator']=m[metric]['denominator']
        item['quality_graded']=m['quality']['graded'];item['latency_observed']=m['latency_ms']['observed']
        comparison.append(item)
    (folder/'comparison.json').write_text(json.dumps({'label':label,'rows':comparison},indent=2))
    with (folder/'comparison.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(comparison[0]));writer.writeheader();writer.writerows(comparison)
    for name,title,metric,key in definitions:
        fig,ax=plt.subplots(figsize=(8,4))
        for i,mode in enumerate(modes):
            value=metrics[mode][metric][key]
            population=metrics[mode][metric]
            count=population.get('denominator',population.get('graded',population.get('observed',0)))
            if value is None: ax.text(i,0.04,f'N/A\nn={count}',ha='center',transform=ax.get_xaxis_transform())
            else:
                ax.bar(i,value,color={'A':'#64748b','B':'#2563eb','C':'#0f766e'}[mode])
                ax.annotate(f'{value:.3g}\nn={count}',(i,value),ha='center',va='bottom')
        ax.set_xticks(range(3),modes);ax.set_xlim(-.6,2.6);ax.set_ylabel(title)
        if key=='rate':ax.set_ylim(0,1.12)
        if name=='quality':ax.set_ylim(0,4.4)
        fig.suptitle(title);fig.text(.5,.015,label,ha='center',fontsize=8)
        fig.tight_layout(rect=(0,.06,1,.95));fig.savefig(folder/(name+'.png'));plt.close(fig)
    (folder/'PRESENTATION.md').write_text('# '+label+'\n\n'
        +f"Scheduled: {summary['all_scheduled']['attempts']}; recorded: {len(rows)}; "
        +f"unreviewed: {summary['coverage']['unreviewed']}; uncertain: {summary['coverage']['uncertain']}.\n\n"
        +'See comparison.csv/JSON for rates and denominators; records.csv/JSON for row-level data. '
        +'N/A is not zero. Error and exposure coverage must accompany rates. '
        +'Latency includes all saved numeric route times, including failed routes. '
        +'Paired/common-evaluable and all-scheduled populations remain separate in summary.json.\n\n'
        +'review-template.json contains blank judgments and is NOT an approved review. '
        +'Fill actual reviewer/notes and inspect review-packets.json before import. '
        +'Synthetic charts cannot establish model accuracy, resistance or a winning defense.\n')
