import json
from flask import render_template, send_from_directory, request, redirect, send_file, safe_join, g
import jinja2
import os
import re
import collections
from datetime import datetime, date
import urllib
import subprocess
import unicodedata
import string

here = os.path.dirname(os.path.abspath(__file__))

class scute:
    hooks = {}
    def __init__(self, options, flaskServer):
        self.options = options
        self.server = flaskServer
        my_loader = jinja2.ChoiceLoader([
            self.server.jinja_loader,
            jinja2.FileSystemLoader(here + '/default_templates')
        ])
        self.server.jinja_loader = my_loader
        self.server.add_url_rule('/', 'index', self.deviceListView)
        self.server.add_url_rule('/config', 'deviceConfig', self.deviceConfigView, False, methods=["GET", "POST"])
        self.server.add_url_rule('/applyPreset', 'applyPreset', self.applyPresetView, False, methods=["GET", "POST"])
        self.server.add_url_rule('/presets', 'presets', self.presets, methods=["GET", "POST"])
        self.server.add_url_rule('/scute/<path:filename>', 'static_assets', self.static_assets)
        self.server.add_url_rule('/scripts', 'scripts', self.scriptsView, False, methods=["GET", "POST"])
        self.server.add_url_rule('/scripts/<script>', 'script', self.script, False, methods=["GET", "POST"])
    def getConfigSchema(self):
        configSchema = {}
        with open(self.options["configSchema"]) as configSchema:  

            configSchema = json.load(configSchema)

            fields = {}
            # Assign default orders
            for category in configSchema:
                if "order" not in configSchema[category]:
                    self.getConfigSchema()[category]["order"] = 0
                for field in configSchema[category]["fields"]:

                    fields[field] = configSchema[category]["fields"][field]
                    if "order" not in fields[field]:
                        fields[field]["order"] = 0
        return configSchema
    def getReportSchema(self):
        with open(self.options["reportSchema"]) as reportSchema:  
            return json.load(reportSchema)
    def getReportFields(self):
        # Extract from categories to get quick access to fields
        fields = {}
        reportSchema = self.getReportSchema()
        for category in reportSchema:
            if "order" not in reportSchema[category]:
                reportSchema[category]["order"] = 0
            for field in reportSchema[category]["fields"]:
                fields[field] = reportSchema[category]["fields"][field]
                if "order" not in fields[field]:
                    fields[field]["order"] = 0
        return fields
    def getActions(self):
        with open(self.options["actionsSchema"]) as actionsSchema: 
            actions = json.load(actionsSchema)
            for key,value in actions.items():
                if "list" in value and not isinstance(value["list"], collections.Mapping):
                    actions[key]["list"] = self.hooks["get_list__" + value["list"]]()
            return actions
    def getDeviceReport(self, deviceID):
        reportValues = {}
        # First try to get all fields, then overwrite with specific ones
        try:
            reportValues = self.hooks["get_report_fields"](deviceID)
        except:
            pass
        for field in self.getReportFields():
            try:
                reportValues[field] = self.hooks["get_report_field__" + field](deviceID)
            except:
                pass
        return reportValues
    
    def static_assets(self, filename):
        return send_from_directory(here + "/client_side/", filename)
    
    def registerHook(self, hookName, hookFunction):
        self.hooks[hookName] = hookFunction
    
    def getDevices(self):
        return self.hooks["get_devices"]()
    
    def getAllDeviceReports(self):
        deviceReports = {}
        for device in self.getDevices():
            deviceReports[device] = self.getDeviceReport(device)
        return deviceReports

    def deviceListView(self):
        return render_template("list.html", title="Horizon",reportValues=self.getAllDeviceReports(), reportSchema=self.getReportSchema(), presetValues=self.getAllPresetValues(), actions=self.getActions(), timeLoaded=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    def getAllPresetValues(self):
        # scan the preset directory and return value label pairs
        if not os.path.exists('presets'):
            return [{"value": "", "label": "No Presets Found"}]
        pathContent = os.listdir('presets')
        replyValues = []
        for file in pathContent:
            fileParts = file.split(".")
            replyValues.append({"value": file, "label": fileParts[0]})
        
        if replyValues == []:
            replyValues = [{"value": "", "label": "No Presets Found"}]
        return replyValues

    def deviceConfigView(self):


        device = request.args.getlist("devices[]")[0]

        # Save config
        if request.method == "POST":
            try:
                # Check if saving preset
                if "preset" in request.form:
                    # Go to presets page
                    presetQuery = self.processFormTypes(request.form)
                    presetQueryJSON = json.dumps(presetQuery)
                    return redirect("/presets?config=" + presetQueryJSON, code=302)
                else:
                    self.hooks["save_config"](device, self.processFormTypes(request.form))
                    if "redirect" in g:
                        return redirect(g.redirect)


            except:
                pass

        # Load existing config and render form
        currentConfig = {}
        try:
            currentConfig = self.hooks["read_config"](device)
        except:
            pass
    

        return render_template("config.html", title="Configuration", schema=self.getConfigSchema(), device=device, current=currentConfig)

    def applyPresetView(self):
        devices = request.args.getlist("devices[]")
        preset = request.args.get("value")

        if request.method == "POST":
            form = self.processFormTypes(request.form)
            for device in devices:
                deviceConfig = self.hooks["read_config"](device)
                for field,value in form.items():
                    deviceConfig[field] = value
                self.hooks["save_config"](device, deviceConfig)
            return redirect("/")

        presetDirectory = ""

        if("presetsDirectory" in self.options):
            presetDirectory = self.options["presetsDirectory"]
        else:
            presetDirectory = 'presets/'

        with open(presetDirectory + preset, "r") as f1:
                presetRaw = f1.read()
                presetJSON = json.loads(presetRaw)

        presetSchema = self.filterOutFieldsWithBooleanAttribute(self.getConfigSchema(), "excludeFromPresets")

        return render_template("applyPreset.html", title="Apply preset", schema=presetSchema, devices=devices, preset=preset, current = presetJSON)


    def filterOutFieldsWithBooleanAttribute(self, fullSchema, excludeAttribute):

        filteredSchema = {}

        for thisCategory in fullSchema.keys(): # loop categories
            filteredSchema[thisCategory] = fullSchema[thisCategory]
            filteredFields = {}

            for fieldName in fullSchema[thisCategory]["fields"]: #loop fields
                               
                if (excludeAttribute in fullSchema[thisCategory]["fields"][fieldName] 
                    and fullSchema[thisCategory]["fields"][fieldName][excludeAttribute] == True):
                    print("filtering out " + fieldName)

                else:
                    #only add fields that no not match.
                    filteredFields[fieldName] = fullSchema[thisCategory]["fields"][fieldName]

            filteredSchema[thisCategory]["fields"] = filteredFields
            if len(filteredFields) == 0:
                # remove the category..
                del(filteredSchema[thisCategory])
            else:
                # update the fields.
                filteredSchema[thisCategory]["fields"] = filteredFields
                    
        return filteredSchema


    def presets(self, current=None):

        presetDirectory = ""

        if("presetsDirectory" in self.options):
            presetDirectory = self.options["presetsDirectory"]
        else:
            presetDirectory = 'presets/'

        if not os.path.exists(presetDirectory):
            os.makedirs(presetDirectory)

        # Check if deleting and delete preset if yes
        if request.args.get('delete'):
            delete = request.args.get('delete')
            os.remove(presetDirectory + "/" + delete + ".json") 

        # Check if query contains a preset (from the config page)

        prefill = {}

        if request.args.get("config"):
            prefill = json.loads(request.args.get("config"))

        if request.method == "POST":
            if "paste" in request.form:
                prefill = json.loads(request.form["paste"])
            else:
                saved = self.processFormTypes(request.form)
                safeName = re.sub('[^a-zA-Z-_0-9]+', ' ', saved["presetName"])
                safeName = safeName.replace(" ", "_")
                saved["presetID"] = safeName
                with open(presetDirectory + safeName + ".json" , 'w') as presetFile:
                    json.dump(saved, presetFile)

        presetFilesNames = os.listdir(presetDirectory)
        presetFilesNames = sorted(presetFilesNames, reverse=False)

        presetFiles = []
        for file in presetFilesNames:
            with open(presetDirectory + file, "r") as f1:
                fileRaw = f1.read()
                fileJSON = json.loads(fileRaw)
                presetFiles.append(fileJSON)
        
        presetSchema = self.filterOutFieldsWithBooleanAttribute(self.getConfigSchema(), "excludeFromPresets")

        return render_template("presets.html", title="Presets", presets=presetFiles, schema=presetSchema, current=prefill)



    def script(self, script):

        scriptsDirectory = ""

        if("scriptsDirectory" in self.options):
            scriptsDirectory = self.options["scriptsDirectory"]
        else:
            scriptsDirectory = 'scripts/'


        scriptSchema = {}
        with open(scriptsDirectory + "/" + script, "r") as f1:
            fileRaw = f1.read()
            scriptSchema = json.loads(fileRaw)

        if request.args.get("command"):
            currentCommand = int(request.args.get("command"))
            nextCommand = currentCommand + 1
        else:
            currentCommand = -1
            nextCommand = 0

        output = ""

        if currentCommand > 0:
            commandToRun = currentCommand - 1
            # Run command

            # Check if any parameters have been passed in

            command = scriptSchema["commands"][commandToRun]["command"]
            output = ""
            for key,value in request.args.items():
                command = command.replace("${"+key+"}", value)
            p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = p.communicate()
            if stdout:
                output = stdout
                error = False
            else:
                output = stderr
                error = True

        return render_template("script.html", title=scriptSchema["name"], script=scriptSchema, nextCommand = nextCommand, fileName=script, output=output, error = error)

    def scriptsView(self):

        scriptsDirectory = ""

        if("scriptsDirectory" in self.options):
            scriptsDirectory = self.options["scriptsDirectory"]
        else:
            scriptsDirectory = 'scripts/'

        try:
            scriptsFileNames = os.listdir(scriptsDirectory)
            scriptsFileNames = sorted(scriptsFileNames, reverse=False)
        except:
            scriptsFileNames = []

        scripts = []

        for file in scriptsFileNames:
            with open(scriptsDirectory + "/" + file, "r") as f1:
                fileRaw = f1.read()
                fileJSON = json.loads(fileRaw)
                fileJSON["fileName"] = file
                scripts.append(fileJSON)

        return render_template("scriptsView.html", title="Scripts", scripts=scripts)

    def expandJSON(self, json):
        # Expand a JSON object with dot based keys into a nested JSON
        expanded = {}
        for key,value in json.items():
            output = expanded
            parts = key.split(".")
            for index,part in enumerate(parts,start=1):
                if part not in output:
                    output[part] = {}
                if index == len(parts):
                    output[part] = value
                output = output[part]
        return expanded
    def flattenJSON(self, object):
        out = {}
        def flatten(x, name=''):
            if type(x) is dict:
                for a in x:
                    flatten(x[a], name + a + '.')
            elif type(x) is list:
                i = 0
                for a in x:
                    flatten(a, name + str(i) + '.')
                    i += 1
            else:
                out[name[:-1]] = x

        flatten(object)
        return out
    def processFormTypes(self, formObject):

        form = formObject.to_dict()

        # Convert a submitted form to have the correct types (booleans only for now)  
        output = {}

        for key,value in form.items():
            if value == "notselected":
                value = False
            if value == "selected":
                value = True
            output[key] = value
        
        return output
