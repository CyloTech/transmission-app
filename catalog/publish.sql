-- Run after the supported import with --admin-only and without --set-default.
-- No customer instance or allocation rows are modified.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
DO $$
DECLARE
    baseline app_versions%ROWTYPE;
    candidate app_versions%ROWTYPE;
    application apps%ROWTYPE;
    changed integer;
    release_notes text := 'Adds UDP forwarding for incoming peer connections and DHT. Keeps the peer port mapped correctly after updates and preserves existing Transmission settings. Update Transmission from Appbox to apply these changes. The assigned peer port number may change and is configured automatically.';
    port_template text := '%PORTS|0.TYPE%:%PORTS|0.INTERNAL%:%PORTS|0.EXTERNAL%,%PORTS|1.TYPE%:%PORTS|1.INTERNAL%:%PORTS|1.EXTERNAL%';
BEGIN
    SELECT * INTO STRICT application FROM apps WHERE id=77 FOR UPDATE;
    SELECT * INTO STRICT baseline FROM app_versions
      WHERE id=1242 AND app_id=77 AND version='4.1.2' FOR UPDATE;
    SELECT * INTO STRICT candidate FROM app_versions
      WHERE app_id=77 AND version='4.1.2-1' FOR UPDATE;

    IF application.display_name <> 'Transmission'
       OR application.version <> '4.1.0' OR application.tag <> '4.1.0'
       OR application."Image" <> 'transmission'
       OR application."TCPPortRange" IS DISTINCT FROM '80'
       OR application."TCPDynamicPorts" IS DISTINCT FROM 1
       OR COALESCE(application."CombinedDynamicPorts",0) <> 0
       OR md5((to_jsonb(application)-ARRAY['version','tag','TCPDynamicPorts','CombinedDynamicPorts','updated_at'])::text)
          <> '233d4ab81199aef2d155b652711f9ccb'
       OR md5((to_jsonb(baseline)-ARRAY['is_default','updated_at'])::text)
          <> '7c4ee4ad6b050396a096217f127fb3de'
       OR baseline.is_default IS DISTINCT FROM 1
       OR candidate.is_default IS DISTINCT FROM 0
       OR candidate.admin_only IS DISTINCT FROM 1
       OR candidate.enabled IS DISTINCT FROM 1
       OR candidate.tag <> '4.1.2-1' OR candidate.image <> 'transmission'
       OR candidate.installed_image_digest IS DISTINCT FROM 'repo.cylo.net/transmission@sha256:6f366e613e04b2999cb1ecb0ad41838dc625743e8b0f3cb998fa75f429476644'
       OR candidate.tcp_port_range IS DISTINCT FROM '80'
       OR candidate.tcp_dynamic_ports IS DISTINCT FROM 0
       OR candidate.combined_dynamic_ports IS DISTINCT FROM 1
       OR candidate.udp_port_range IS NOT NULL
       OR candidate.combined_port_range IS NOT NULL
       OR COALESCE(candidate.udp_dynamic_ports,0) <> 0
       OR (SELECT count(*) FROM app_versions WHERE app_id=77 AND is_default=1) <> 1
    THEN
        RAISE EXCEPTION 'Transmission catalogue prior state or candidate differs from reviewed release';
    END IF;

    IF ROW(candidate.app_slots,candidate.memory,candidate.memory_swap,
           candidate.memory_reservation,candidate.cpus,candidate.min_memory,
           candidate.min_cpus,candidate.pids_limit,candidate.init,
           candidate.privileged,candidate.cap_add,candidate.cap_drop,
           candidate.custom_field_preinstall_description,candidate.custom_field_postinstall_description)
       IS DISTINCT FROM
       ROW(baseline.app_slots,baseline.memory,baseline.memory_swap,
           baseline.memory_reservation,baseline.cpus,baseline.min_memory,
           baseline.min_cpus,baseline.pids_limit,baseline.init,
           baseline.privileged,baseline.cap_add,baseline.cap_drop,
           baseline.custom_field_preinstall_description,baseline.custom_field_postinstall_description)
    THEN
        RAISE EXCEPTION 'Transmission resource or installation-description parity failed';
    END IF;

    IF (SELECT count(*) FROM appenvironmentvars WHERE app_id=77) <> 1
       OR NOT EXISTS (SELECT 1 FROM appenvironmentvars WHERE id=75 AND app_id=77
                      AND "Key"='LISTENING_PORT' AND "Value"='%PORTS|0.EXTERNAL%'
                      AND template_type='instance' AND version IS NULL)
    THEN
        RAISE EXCEPTION 'Transmission environment templates differ from reviewed baseline';
    END IF;

    INSERT INTO appenvironmentvars(app_id,"Key","Value",template_type,version)
      VALUES(77,'APPBOX_PORTS',port_template,'instance',candidate.version);
    GET DIAGNOSTICS changed = ROW_COUNT;
    IF changed <> 1 THEN RAISE EXCEPTION 'Expected one version-specific port template'; END IF;

    UPDATE app_versions SET is_default=0,updated_at=CURRENT_TIMESTAMP
      WHERE id=baseline.id AND is_default=1;
    GET DIAGNOSTICS changed = ROW_COUNT;
    IF changed <> 1 THEN RAISE EXCEPTION 'Expected one previous default'; END IF;

    UPDATE app_versions SET changes=release_notes,admin_only=0,is_default=1,updated_at=CURRENT_TIMESTAMP
      WHERE id=candidate.id AND admin_only=1 AND is_default=0;
    GET DIAGNOSTICS changed = ROW_COUNT;
    IF changed <> 1 THEN RAISE EXCEPTION 'Expected one candidate'; END IF;

    UPDATE apps SET version=candidate.version,tag=candidate.tag,"TCPDynamicPorts"=0,
      "CombinedDynamicPorts"=1,updated_at=CURRENT_TIMESTAMP::text WHERE id=77 AND version='4.1.0';
    GET DIAGNOSTICS changed = ROW_COUNT;
    IF changed <> 1 THEN RAISE EXCEPTION 'Expected one Transmission app'; END IF;

    IF (SELECT count(*) FROM app_versions WHERE app_id=77 AND is_default=1) <> 1
       OR NOT EXISTS (SELECT 1 FROM app_versions WHERE id=candidate.id AND is_default=1
                      AND enabled=1 AND admin_only=0 AND changes=release_notes)
       OR NOT EXISTS (SELECT 1 FROM appenvironmentvars WHERE app_id=77 AND version=candidate.version
                      AND "Key"='APPBOX_PORTS' AND "Value"=port_template AND template_type='instance')
    THEN
        RAISE EXCEPTION 'Transmission publication postcondition failed';
    END IF;
    RAISE NOTICE 'Published Transmission % (ID %)',candidate.version,candidate.id;
END $$;
COMMIT;
