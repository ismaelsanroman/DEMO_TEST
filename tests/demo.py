print(f"Surviving mutants (job_id, module, operator):")
for job in jobs:
    # Si es un job dict, extraemos job_id y la lista de mutaciones
    if isinstance(job, dict):
        job_id = job.get("job_id", "<no-job_id>")
        muts   = job.get("mutations") or job.get("results") or []
    # Si es una lista, no hay job_id, pero la tratamos como lista de mutaciones
    elif isinstance(job, list):
        job_id = "<no-job_id>"
        muts   = job
    else:
        # cualquier otro tipo, lo saltamos
        continue

    for m in muts:
        if m.get("test_outcome") != "killed":
            module = m.get("module_path", "<sin módulo>")
            op     = m.get("operator_name", "<sin operador>")
            print(f"  • job_id={job_id}, módulo={module}, operador={op}")

