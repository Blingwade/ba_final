# imports
import docker
import time
import requests
import subprocess
import json
import numpy

run_count = 20

def manage_influxdb():
    # Docker-Client initialisieren
    client = docker.from_env()

    try:
        # InfluxDB-Container starten
        print("Starte InfluxDB-Container...")
        container = client.containers.run(
            image="influxdb:latest",
            name="influxdb-container",
            ports={"8086/tcp": 8086},
            environment={
                "DOCKER_INFLUXDB_INIT_MODE": "setup",
                "DOCKER_INFLUXDB_INIT_USERNAME": "admin",
                "DOCKER_INFLUXDB_INIT_PASSWORD": "password",
                "DOCKER_INFLUXDB_INIT_ORG": "example_org",
                "DOCKER_INFLUXDB_INIT_BUCKET": "example_bucket0",
                "INFLUXD_STORAGE_SERIES_ID_SET_CACHE_SIZE": "0"
            },
            detach=True,
        )
        print(f"InfluxDB-Container gestartet. Container-ID: {container.id}")

        # Wartezeit, bis der Container bereit ist
        time.sleep(5)

        # API-Token erstellen
        print("Erstelle API-Token...")
        create_token_command = [
            "docker", "exec", "-i", "influxdb-container",
            "influx", "auth", "create",
            "--all-access",
            "--user", "admin"
        ]
        result = subprocess.run(create_token_command, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"Fehler beim Erstellen des API-Tokens: {result.stderr}")
            return

        # Debug-Ausgabe, um die komplette Ausgabe des Befehls zu sehen
        print(f"Ausgabe von 'influx auth create':\n{result.stdout}")

        # Extrahiere Token aus der Ausgabe
        token = None
        for line in result.stdout.split("\n"):
            if "admin" in line and len(line.split()) > 2:
                token = line.split()[1]  # Token steht in der zweiten Spalte
                break

        if not token:
            print("Fehler: Konnte API-Token nicht extrahieren.")
            return

        print(f"API-Token: {token}")


        print("Rufe Org-ID ab...")
        org_url = "http://localhost:8086/api/v2/orgs"
        headers = {
            "Authorization": f"Token {token}",
            "Accept": "application/json"
        }

        org_response = requests.get(org_url, headers=headers)
        if org_response.status_code == 200:
            org_data = org_response.json()
            org_id = org_data["orgs"][0]["id"]  # Die erste Organisation nehmen
            print(f" Org-ID: {org_id}")
        else:
            print(f" Fehler beim Abrufen der Org-ID: {org_response.status_code}, {org_response.text}")
            return

        # **Zusätzliche Buckets erstellen**
        print("Erstelle zusätzliche Buckets...")
        influxdb_url = "http://localhost:8086/api/v2/buckets"

        buckets = ["example_bucket1", "example_bucket2"]

        for bucket in buckets:
            data = json.dumps({
                "orgID": org_id,  # **Hier verwenden wir die Org-ID**
                "name": bucket,
                "retentionRules": []
            })
            response = requests.post(influxdb_url, headers=headers, data=data)

            if response.status_code == 201:
                print(f"Bucket {bucket} erfolgreich erstellt.")
            else:
                print(f"Fehler beim Erstellen von {bucket}: {response.status_code}, {response.text}")
        
        starttime = time.time_ns()
        for run_i in range(0, run_count):
            prefix = "RUN_" + str(run_i) + "_"
            # Daten in die Datenbank schreiben
            print("Schreibe Daten in die Datenbank...")
            influxdb_url = "http://localhost:8086/api/v2/write"
            params = {
                "bucket": "example_bucket0",
                "org": "example_org",
                "precision": "s",
            }
            headers = {
                "Authorization": f"Token {token}",
                "Content-Type": "text/plain",
            }

            f = open(prefix + "influxdata0.txt","r")
            data = f.read().strip()
            f.close()

            response = requests.post(influxdb_url, params=params, headers=headers, data=data)

            if response.status_code == 204:
                print("Daten in example_bucket0 erfolgreich geschrieben.")
            else:
                print(f"Fehler beim Schreiben der Daten: {response.status_code}, {response.text}")

            
            params = {
                "bucket": "example_bucket1",
                "org": "example_org",
                "precision": "s",
            }
            f = open(prefix + "influxdata1.txt","r")
            data = f.read().strip()
            f.close()

            response = requests.post(influxdb_url, params=params, headers=headers, data=data)

            if response.status_code == 204:
                print("Daten in example_bucket0 erfolgreich geschrieben.")
            else:
                print(f"Fehler beim Schreiben der Daten: {response.status_code}, {response.text}")

            params = {
                "bucket": "example_bucket2",
                "org": "example_org",
                "precision": "s",
            }
            f = open(prefix + "influxdata2.txt","r")
            data = f.read().strip()
            f.close()

            response = requests.post(influxdb_url, params=params, headers=headers, data=data)

            if response.status_code == 204:
                print("Daten in example_bucket2 erfolgreich geschrieben.")
            else:
                print(f"Fehler beim Schreiben der Daten: {response.status_code}, {response.text}")

        insert_time = time.time_ns() - starttime
        print("INSERT_TIME=" + str(insert_time)+"\n")
        f = open("inserttime.txt","a")
        f.write("Insert time for " + str(run_count) + " million entries: " + str(insert_time))
        f.close()
        # Query ausführen
        print("Führe Query aus, um alle homes abzurufen...")
        query_url = "http://localhost:8086/api/v2/query"
        #query = '''
        #from(bucket: "example_bucket")
        #  |> range(start: 0)
        #  |> filter(fn: (r) => r._measurement == "home")
        #'''

        try: 
            yourinput = input("which function do you want to test\n")

        except e:
            print("no such query found")
        with open("queries.json", "r") as queryfile:
            queries = json.load(queryfile)
            print(queries)
            logs = open("influxqueryresponses.txt", "a")
            for item in queries:

                print(item)
                query = queries[item]["influx"]
                #sumquery = json.loads(queryfile.read())["sum"]["influx"]
                print(query)

                headers.update({"Content-Type": "application/vnd.flux", "Accept": "application/csv"})


                # Hier container stoppen und neu starten, damit cache geleert wird, selbes noch bei postgres machen
                times = []
                query_response = ""
                for i in range(100):
                    container.stop()
                    time.sleep(1)
                    container.start()
                    time.sleep(1)
                    for _ in range(10):
                        try:
                            response = requests.get(influxdb_url, timeout=3)
                            if response.status_code == 200:
                                print("InfluxDB ist wieder verfügbar!")
                                break
                        except requests.exceptions.ConnectionError:
                            print("Warte auf InfluxDB...")
                            time.sleep(1)

                    starttime = time.time_ns()
                    query_response = requests.post(query_url, params={"org": "example_org"}, headers=headers, data=query)
                    endtime = time.time_ns()

                    times.append(endtime-starttime)

                numeric_value = None

               # Antwort in Zeilen aufteilen
                lines = query_response.text.strip().split("\n")

                # Spaltennamen aus der ersten Zeile extrahieren
                column_names = [col.strip() for col in lines[0].split(",")]  # Leerzeichen entfernen
                # Prüfen, an welcher Position die Spalte "_value" ist
                try:
                    value_index = column_names.index("_value")  # Die Spaltennummer von "_value" holen
                except ValueError:
                    print("Fehler: Keine '_value'-Spalte in der Antwort gefunden")
                    value_index = None

                # Falls die Spalte gefunden wurde, extrahieren wir die Zahl aus der letzten Datenzeile
                if value_index is not None and len(lines) > 1:
                    last_data_line = lines[-1].split(",")  # Letzte Zeile aufteilen
                    if len(last_data_line) > value_index:  # Sicherstellen, dass die Spalte existiert
                        numeric_value = last_data_line[value_index].strip()  # Den Wert holen
                    else:
                        print("Fehler: '_value'-Spalte nicht in der letzten Zeile gefunden")

                print(query_response.text)

                if query_response.status_code == 200:
                    logs.write(str(item)+"," + str(numpy.average(times))  + "," + str(numeric_value) + "\n")
                else:
                    print(f"Fehler bei der Query: {query_response.status_code}, {query_response.text}")

    except Exception as e:
        print(f"Fehler: {e}")

    finally:
        # Warte 20 Sekunden, bevor der Container gestoppt wird
        #print("Warte 20 Sekunden...")
        input("waiting for input to stop the program")

        # Container stoppen und löschen
        print("Stoppe den Container...")
        try:
            
            container_name = "influxdb-container"
            result = subprocess.run(["docker", "ps", "-s"], capture_output=True, text=True)
            print(container.stats(decode=None,stream = False)['memory_stats'])
            f = open("influxcontainerstats.txt","a")
            f.write(str(result.stdout))
            f.close()
            container.stop()
            container.remove()
            print("Container erfolgreich gestoppt und gelöscht.")
            print("Laufzeit der Query: " + str(endtime - starttime))

        except Exception as e:
            print(f"Fehler beim Stoppen/Löschen des Containers: {e}")

if __name__ == "__main__":
    manage_influxdb()
