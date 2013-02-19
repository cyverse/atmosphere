package org.iplantcollaborative.atmo.client.estevewrapper;
//TODO: Image & Instance toString()
public class AtmoObject {
	private String id, name, desc, tags;

	public AtmoObject(String id, String name, String desc, String tags) {
		super();
		this.id = id;
		this.name = name;
		this.desc = desc;
		this.tags = tags;
	}

	public String getId() {
		return id;
	}

	public void setId(String id) {
		this.id = id;
	}

	public String getName() {
		return name;
	}

	public void setName(String name) {
		this.name = name;
	}

	public String getDesc() {
		return desc;
	}

	public void setDesc(String desc) {
		this.desc = desc;
	}

	public String getTags() {
		return tags;
	}

	public void setTags(String tags) {
		this.tags = tags;
	}

}

class AtmoApp extends AtmoObject {
	String type, platform, create_time, icon_path, machine_image_id, creator, ramdisk_id, min_req, category, kernelid, version;
	boolean is_sys_app;
	
	public AtmoApp(String type, String platform, String create_time,
			String name, String icon_path, String machine_image_id,
			String creator, String tags, String description, String ramdisk_id,
			String min_req, String category, String kernelid, String version,
			String appid, boolean is_sys_app) {
		super(appid, name, description, tags);
		this.type = type;
		this.platform = platform;
		this.create_time = create_time;
		this.icon_path = icon_path;
		this.machine_image_id = machine_image_id;
		this.creator = creator;
		this.ramdisk_id = ramdisk_id;
		this.min_req = min_req;
		this.category = category;
		this.kernelid = kernelid;
		this.version = version;
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
	public boolean isIs_sys_app() {
		return is_sys_app;
	}
	public void setIs_sys_app(boolean is_sys_app) {
		this.is_sys_app = is_sys_app;
	}

	@Override
	public String toString() {
		return "AtmoApp [type=" + type + ", platform=" + platform
				+ ", create_time=" + create_time + ", name=" + getName()
				+ ", icon_path=" + icon_path + ", machine_image_id="
				+ machine_image_id + ", creator=" + creator + ", tags=" + getTags()
				+ ", description=" + getDesc() + ", ramdisk_id=" + ramdisk_id
				+ ", min_req=" + min_req + ", category=" + category
				+ ", kernelid=" + kernelid + ", version=" + version
				+ ", appid=" + getId() + ", is_sys_app=" + is_sys_app
				+ ", getType()=" + getType() + ", getPlatform()="
				+ getPlatform() + ", getCreate_time()=" + getCreate_time()
				+ ", getName()=" + getName() + ", getIcon_path()="
				+ getIcon_path() + ", getMachine_image_id()="
				+ getMachine_image_id() + ", getCreator()=" + getCreator()
				+ ", getTags()=" + getTags() + ", getDescription()="
				+ getDesc() + ", getRamdisk_id()=" + getRamdisk_id()
				+ ", getMin_req()=" + getMin_req() + ", getCategory()="
				+ getCategory() + ", getKernelid()=" + getKernelid()
				+ ", getVersion()=" + getVersion() + ", getAppid()="
				+ getId() + ", isIs_sys_app()=" + isIs_sys_app()
				+ ", getClass()=" + getClass() + ", hashCode()=" + hashCode()
				+ ", toString()=" + super.toString() + "]";
	}
}

class AtmoImage extends AtmoObject {

	private String location, owner, state, arch, type, ramdisk, kernel;
	private boolean is_public;

	public AtmoImage(String name, String desc, String tags, String id,
			String location, String owner, String state, String arch,
			String type, String ramdisk, String kernel, boolean is_public) {
		super(id, name, desc, tags);
		this.location = location;
		this.owner = owner;
		this.state = state;
		this.arch = arch;
		this.type = type;
		this.ramdisk = ramdisk;
		this.kernel = kernel;
		this.is_public = is_public;
	}

	public String getLocation() {
		return location;
	}

	public String getOwner() {
		return owner;
	}

	public String getState() {
		return state;
	}

	public String getArch() {
		return arch;
	}

	public String getType() {
		return type;
	}

	public String getRamdisk() {
		return ramdisk;
	}

	public String getKernel() {
		return kernel;
	}

	public boolean isIs_public() {
		return is_public;
	}

	@Override
	public String toString() {
		return "AtmoImage [name=" + getName() + ", desc=" + getDesc() + ", tags=" + getTags()
				+ ", id=" + getId() + ", location=" + location + ", owner=" + owner
				+ ", state=" + state + ", arch=" + arch + ", type=" + type
				+ ", ramdisk=" + ramdisk + ", kernel=" + kernel
				+ ", is_public=" + is_public + "]";
	}
	
	
	
}

class AtmoInstance extends AtmoObject {
	String instance_state, instance_ami_launch_index, instance_placement,
			instance_product_codes, group_id, reservation_owner_id,
			reservation_id, instance_private_dns_name, instance_launch_time,
			instance_key_name, instance_kernel, instance_ramdisk,
			instance_image_id, instance_num, instance_image_name,
			instance_public_dns_name, instance_instance_type;

	public AtmoInstance(String instance_state, String instance_description,
			String instance_tags, String instance_ami_launch_index,
			String instance_placement, String instance_product_codes,
			String group_id, String reservation_owner_id,
			String reservation_id, String instance_private_dns_name,
			String instance_name, String instance_launch_time,
			String instance_key_name, String instance_kernel,
			String instance_ramdisk, String instance_image_id,
			String instance_num, String instance_image_name,
			String instance_public_dns_name, String instance_id,
			String instance_instance_type) {
		super(instance_id, instance_name, instance_description, instance_tags);
		this.instance_state = instance_state;
		this.instance_ami_launch_index = instance_ami_launch_index;
		this.instance_placement = instance_placement;
		this.instance_product_codes = instance_product_codes;
		this.group_id = group_id;
		this.reservation_owner_id = reservation_owner_id;
		this.reservation_id = reservation_id;
		this.instance_private_dns_name = instance_private_dns_name;
		this.instance_launch_time = instance_launch_time;
		this.instance_key_name = instance_key_name;
		this.instance_kernel = instance_kernel;
		this.instance_ramdisk = instance_ramdisk;
		this.instance_image_id = instance_image_id;
		this.instance_num = instance_num;
		this.instance_image_name = instance_image_name;
		this.instance_public_dns_name = instance_public_dns_name;
		this.instance_instance_type = instance_instance_type;
	}

	public String getInstance_state() {
		return instance_state;
	}

	public void setInstance_state(String instance_state) {
		this.instance_state = instance_state;
	}

	public String getInstance_ami_launch_index() {
		return instance_ami_launch_index;
	}

	public void setInstance_ami_launch_index(String instance_ami_launch_index) {
		this.instance_ami_launch_index = instance_ami_launch_index;
	}

	public String getInstance_placement() {
		return instance_placement;
	}

	public void setInstance_placement(String instance_placement) {
		this.instance_placement = instance_placement;
	}

	public String getInstance_product_codes() {
		return instance_product_codes;
	}

	public void setInstance_product_codes(String instance_product_codes) {
		this.instance_product_codes = instance_product_codes;
	}

	public String getGroup_id() {
		return group_id;
	}

	public void setGroup_id(String group_id) {
		this.group_id = group_id;
	}

	public String getReservation_owner_id() {
		return reservation_owner_id;
	}

	public void setReservation_owner_id(String reservation_owner_id) {
		this.reservation_owner_id = reservation_owner_id;
	}

	public String getReservation_id() {
		return reservation_id;
	}

	public void setReservation_id(String reservation_id) {
		this.reservation_id = reservation_id;
	}

	public String getInstance_private_dns_name() {
		return instance_private_dns_name;
	}

	public void setInstance_private_dns_name(String instance_private_dns_name) {
		this.instance_private_dns_name = instance_private_dns_name;
	}

	public String getInstance_launch_time() {
		return instance_launch_time;
	}

	public void setInstance_launch_time(String instance_launch_time) {
		this.instance_launch_time = instance_launch_time;
	}

	public String getInstance_key_name() {
		return instance_key_name;
	}

	public void setInstance_key_name(String instance_key_name) {
		this.instance_key_name = instance_key_name;
	}

	public String getInstance_kernel() {
		return instance_kernel;
	}

	public void setInstance_kernel(String instance_kernel) {
		this.instance_kernel = instance_kernel;
	}

	public String getInstance_ramdisk() {
		return instance_ramdisk;
	}

	public void setInstance_ramdisk(String instance_ramdisk) {
		this.instance_ramdisk = instance_ramdisk;
	}

	public String getinstance_image_id() {
		return instance_image_id;
	}

	public void setinstance_image_id(String instance_image_id) {
		this.instance_image_id = instance_image_id;
	}

	public String getInstance_num() {
		return instance_num;
	}

	public void setInstance_num(String instance_num) {
		this.instance_num = instance_num;
	}

	public String getInstance_image_name() {
		return instance_image_name;
	}

	public void setInstance_image_name(String instance_image_name) {
		this.instance_image_name = instance_image_name;
	}

	public String getInstance_public_dns_name() {
		return instance_public_dns_name;
	}

	public void setInstance_public_dns_name(String instance_public_dns_name) {
		this.instance_public_dns_name = instance_public_dns_name;
	}

	public String getInstance_instance_type() {
		return instance_instance_type;
	}

	public void setInstance_instance_type(String instance_instance_type) {
		this.instance_instance_type = instance_instance_type;
	}

	@Override
	public String toString() {
		return "AtmoInstance [instance_state=" + instance_state
				+ ", instance_description=" + getDesc()
				+ ", instance_tags=" + getTags()
				+ ", instance_ami_launch_index=" + instance_ami_launch_index
				+ ", instance_placement=" + instance_placement
				+ ", instance_product_codes=" + instance_product_codes
				+ ", group_id=" + group_id + ", reservation_owner_id="
				+ reservation_owner_id + ", reservation_id=" + reservation_id
				+ ", instance_private_dns_name=" + instance_private_dns_name
				+ ", instance_name=" + getName()
				+ ", instance_launch_time=" + instance_launch_time
				+ ", instance_key_name=" + instance_key_name
				+ ", instance_kernel=" + instance_kernel
				+ ", instance_ramdisk=" + instance_ramdisk
				+ ", instance_image_id=" + instance_image_id
				+ ", instance_num=" + instance_num + ", instance_image_name="
				+ instance_image_name + ", instance_public_dns_name="
				+ instance_public_dns_name + ", instance_id=" + getId()
				+ ", instance_instance_type=" + instance_instance_type + "]";
	}

}

class AtmoVolume extends AtmoObject {
	String  attach_data_device, status, 
			create_time, attach_data_attach_time, snapshot_id,
			attach_data_instance_id;
	int num, size;

	public AtmoVolume(String id, String tags, String attach_data_device,
			String status, String desc, String name, String create_time,
			String attach_data_attach_time, String snapshot_id,
			String attach_data_instance_id, int num, int size) {
		super(id, name, tags, desc);
		this.attach_data_device = attach_data_device;
		this.status = status;
		this.create_time = create_time;
		this.attach_data_attach_time = attach_data_attach_time;
		this.snapshot_id = snapshot_id;
		this.attach_data_instance_id = attach_data_instance_id;
		this.num = num;
		this.size = size;
	}

	public String getAttach_data_device() {
		return attach_data_device;
	}

	public void setAttach_data_device(String attach_data_device) {
		this.attach_data_device = attach_data_device;
	}

	public String getStatus() {
		return status;
	}

	public void setStatus(String status) {
		this.status = status;
	}

	public String getCreate_time() {
		return create_time;
	}

	public void setCreate_time(String create_time) {
		this.create_time = create_time;
	}

	public String getAttach_data_attach_time() {
		return attach_data_attach_time;
	}

	public void setAttach_data_attach_time(String attach_data_attach_time) {
		this.attach_data_attach_time = attach_data_attach_time;
	}

	public String getSnapshot_id() {
		return snapshot_id;
	}

	public void setSnapshot_id(String snapshot_id) {
		this.snapshot_id = snapshot_id;
	}

	public String getAttach_data_instance_id() {
		return attach_data_instance_id;
	}

	public void setAttach_data_instance_id(String attach_data_instance_id) {
		this.attach_data_instance_id = attach_data_instance_id;
	}

	public int getNum() {
		return num;
	}

	public void setNum(int num) {
		this.num = num;
	}

	public int getSize() {
		return size;
	}

	public void setSize(int size) {
		this.size = size;
	}

	@Override
	public String toString() {
		return "AtmoVolume [id=" + getId() + ", tags=" + getTags()
				+ ", attach_data_device=" + attach_data_device + ", status="
				+ status + ", description=" + getDesc() + ", name=" + getName()
				+ ", create_time=" + create_time + ", attach_data_attach_time="
				+ attach_data_attach_time + ", snapshot_id=" + snapshot_id
				+ ", attach_data_instance_id=" + attach_data_instance_id
				+ ", num=" + num + ", size=" + size + "]";
	}
}
