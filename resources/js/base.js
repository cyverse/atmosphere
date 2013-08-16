/* GLOBALS */
var DEBUG = true;
var version = 'v1';
var api = 'https://howe.iplantc.org:443/resources/v1/';
var user = "esteve";
var token = '8aeb29bd-7112-45d9-8987-964216abb414';
function setAtmoUser(aUser, aToken) {
	user = aUser;
	token = aToken;
}

Number.prototype.toNumberCommaString = function() {
	return this.toFixed(0).replace(/(\d)(?=(\d{3})+\b)/, '$1,');
};

// function postAtmoJSON(param,data) {
// 	$.ajax({
// 		url: api+param,
// 		dataType: 'json',
// 		type: "POST",
// 		data: data, 
//  		headers: {
// 			'X-Auth-User':user,
// 			'X-Auth-Token':token,
// 			'X-Api-Server':api,
// 			'X-Api-Version':version
// 		},
// 		error: function(xhr, textStatus, errorThrown) {
// 			if(DEBUG) {
// 				console.log("JSON ERROR");
// 				console.log(xhr.responseText);
// 				console.log("END JSON ERROR");
// 			}
// 		},
// 		success: function(data) {
// 			parseJSON(data,param);
// 		}
// 	});
// };
// function getAtmoJSON(param, success_callback) {
// 	$.ajax({
// 		url: api+param,
// 		dataType: 'json',
// 		type: "GET",
// 		data: "",
//  		headers: {
// 			'X-Auth-User':user,
// 			'X-Auth-Token':token,
// 			'X-Api-Server':api,
// 			'X-Api-Version':version
// 		},
// 		error: function(xhr, textStatus, errorThrown) {
// 			if(DEBUG) {
// 				console.log("JSON ERROR");
// 				console.log(xhr.responseText);
// 				console.log("END JSON ERROR");
// 			}
// 		},
// 		success: function(data) {
// 			//parseJSON(data,param);
// 			success_callback(data);//Let your function do stuff with data
// 		}
// 	});
// };
// function parseJSON(data, typeOfData) {
// 	var single;
// 	$.each(data.result.value, function(idx,val) {
// 		single = new Object();
// 		switch(typeOfData) {
// 			case "getUserProfile":
// 					$.each(val, function(aKey, aValue) {
// 						single = {key:aKey, value:aValue};
// 						properties.push(single);
// 					});
// 				break;
// 			case "getAppList":
// 				single = {name:val.application_name, desc:val.application_description, machineid:val.machine_image_id, appid:val.application_id, size:val.system_minimum_requirements, icon:val.application_icon_path};
// 				apps.push(single);
// 				break;
// 			case "getImageList":
// 				single = {name:val.image_name, desc:val.image_description, id:val.image_id, owner:val.ownerid, permissions:val.image_is_public, status:val.image_state, tags:val.image_tags};
// 				machines.push(single);
// 				break;
// 			case "getInstanceList":
// 				single = {name:val.instance_name, desc:val.instance_description, id:val.instance_id, machineid:val.instance_image_id, machinename:lookupMachine(val.instance_image_id), ipaddr:val.instance_public_dns_name, status:val.instance_state, size:val.instance_instance_type, launchtime:val.instance_launch_time};
// 				instances.push(single);
// 				break;
// 			case "getVolumeList":
// 				single = {
// 					name:val.name, 
// 					desc:val.description, 
// 					id: val.id, 
// 					size:val.size, 
// 					status:val.status, 
// 					createtime: val.create_time, 
// 					attached_instanceid: (val.attach_data_instance_id === "None") ? "N/A" : val.attach_data_instance_id, 
// 					attached_device: (val.attach_data_device === "None") ? "N/A" : val.attach_data_device, 
// 					attached_time: (val.attach_data_attach_time === "None") ? "N/A" : val.attach_data_time,
// 					tags: (val.tags === "") ? "N/A" : val.tags
// 				};
// 				volumes.push(single);
// 				break;
// 		}
// 	});
// 	console.log(properties);
// }

Atmo.get_credentials = function() {
  var creds = {};
  $.each(Atmo.Utils.current_credentials(), function(key, value) {
    creds[key] = value;
  });
  return creds;
}
