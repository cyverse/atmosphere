package org.iplantcollaborative.atmo.client.estevewrapper;

public class AtmoApp {
	String type, platform, create_time, name, icon_path, machine_image_id,
			creator, tags, description, ramdisk_id, min_req, category,
			kernelid, version, appid;
	boolean is_sys_app;

	public AtmoApp(String type, String platform, String create_time,
			String name, String icon_path, String machine_image_id,
			String creator, String tags, String description, String ramdisk_id,
			String min_req, String category, String kernelid, String version,
			String appid, boolean is_sys_app) {
		super();
		this.type = type;
		this.platform = platform;
		this.create_time = create_time;
		this.name = name;
		this.icon_path = icon_path;
		this.machine_image_id = machine_image_id;
		this.creator = creator;
		this.tags = tags;
		this.description = description;
		this.ramdisk_id = ramdisk_id;
		this.min_req = min_req;
		this.category = category;
		this.kernelid = kernelid;
		this.version = version;
		this.appid = appid;
		this.is_sys_app = is_sys_app;
	}

	public String getType() {
		return type;
	}

	public void setType(String type) {
		this.type = type;
	}

	public String getPlatform() {
		return platform;
	}

	public void setPlatform(String platform) {
		this.platform = platform;
	}

	public String getCreate_time() {
		return create_time;
	}

	public void setCreate_time(String create_time) {
		this.create_time = create_time;
	}

	public String getName() {
		return name;
	}

	public void setName(String name) {
		this.name = name;
	}

	public String getIcon_path() {
		return icon_path;
	}

	public void setIcon_path(String icon_path) {
		this.icon_path = icon_path;
	}

	public String getMachine_image_id() {
		return machine_image_id;
	}

	public void setMachine_image_id(String machine_image_id) {
		this.machine_image_id = machine_image_id;
	}

	public String getCreator() {
		return creator;
	}

	public void setCreator(String creator) {
		this.creator = creator;
	}

	public String getTags() {
		return tags;
	}

	public void setTags(String tags) {
		this.tags = tags;
	}

	public String getDescription() {
		return description;
	}

	public void setDescription(String description) {
		this.description = description;
	}

	public String getRamdisk_id() {
		return ramdisk_id;
	}

	public void setRamdisk_id(String ramdisk_id) {
		this.ramdisk_id = ramdisk_id;
	}

	public String getMin_req() {
		return min_req;
	}

	public void setMin_req(String min_req) {
		this.min_req = min_req;
	}

	public String getCategory() {
		return category;
	}

	public void setCategory(String category) {
		this.category = category;
	}

	public String getKernelid() {
		return kernelid;
	}

	public void setKernelid(String kernelid) {
		this.kernelid = kernelid;
	}

	public String getVersion() {
		return version;
	}

	public void setVersion(String version) {
		this.version = version;
	}

	public String getAppid() {
		return appid;
	}

	public void setAppid(String appid) {
		this.appid = appid;
	}

	public boolean isIs_sys_app() {
		return is_sys_app;
	}

	public void setIs_sys_app(boolean is_sys_app) {
		this.is_sys_app = is_sys_app;
	}

}
