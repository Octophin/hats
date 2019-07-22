document.querySelectorAll(".deviceHeader").forEach(function (element) {

    element.addEventListener("click", function (e) {

        let element = e.currentTarget;

        if (element.getAttribute("data-active")) {

            element.removeAttribute("data-active");

        } else {

            element.setAttribute("data-active", "true");

        }

        let selected = document.querySelectorAll(".deviceHeader[data-active]");

        if (selected.length) {

            document.querySelector(".actions").style.visibility = "visible";
            document.querySelector(".selected-devices .count").innerHTML = selected.length;

        } else {

            document.querySelector(".actions").style.visibility = "hidden";

        }

    });

});

let clearDevices = function () {

    document.querySelector(".actions").style.visibility = "hidden";

    document.querySelectorAll(".deviceHeader[data-active]").forEach(function (element) {

        element.removeAttribute("data-active");

    });

};

document.querySelectorAll("input, select").forEach(function (element) {

    element.addEventListener("change", function (e) {

        if (e.target.value) {

            e.target.setAttribute("data-changed", "true");

        } else {

            e.target.removeAttribute("data-changed");

        }


    });

});

let triggerAction = function (action) {

    let devices = [];
    let queryString = "?";

    document.querySelectorAll(".deviceHeader[data-active]").forEach(function (element, index) {

        let device = element.getAttribute("data-device");

        devices.push(device);

        queryString += "devices[]=" + device + "&";

    });

    document.location.href = action + queryString;

};

let savePreset = function () {

    let values = {};

    document.querySelectorAll("input, select").forEach(function (element) {

        // Ignore if exclude from preset

        if (element.parentElement.getAttribute("data-exlude-from-preset")) {

            return false;

        }

        let name = element.getAttribute("name");
        let value;

        if (element.tagName === "SELECT") {

            value = element.options[element.selectedIndex].value;

        } else {

            value = element.value;

        }

        values[name] = value;

    });

    alert("Not yet implemented but data will be " + JSON.stringify(values));

};

let loadPreset = function (presetID) {

    removeThisClassFromLI('preset-list-item-selected');
    document.getElementById("preset-list-item-" + presetID).classList.add('preset-list-item-selected');

    document.getElementById("presetDeleteWrapper").style.visibility = 'visible';
    document.getElementById("presetForm").style.visibility = 'visible';
    document.getElementById('presetHeading').textContent = presetList[presetID].name;
    document.getElementById('presetDate').textContent = presetList[presetID].date;
    document.getElementById("presetName").value = presetList[presetID].name;
    document.getElementById("preseDescription").value = presetList[presetID].description;
    document.getElementById("presetFields").value = JSON.stringify(presetList[presetID].presets);


};

let addPreset = function () {

    removeThisClassFromLI('preset-list-item-selected');

    document.getElementById("presetDeleteWrapper").style.visibility = 'hidden';
    document.getElementById("presetForm").style.visibility = 'visible';
    document.getElementById('presetHeading').textContent = "Add Preset";
    document.getElementById('presetDate').textContent = '';
    document.getElementById("presetName").value = '';
    document.getElementById("preseDescription").value = '';
    document.getElementById("presetFields").value = '';

};

let deletePreset = function () {

    removeThisClassFromLI('preset-list-item-selected');

    alert("Not yet implemented: deletePreset");

};


function removeThisClassFromLI(thisClass) {
    var target = document.querySelectorAll("li." + thisClass);
    for (var i = 0; i < target.length; i++) {
        target[i].classList.remove(thisClass);
    }
}