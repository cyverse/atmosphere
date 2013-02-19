package org.iplantcollaborative.atmo.client.estevewrapper;
public class AtmoInstance {

	String instance_state, instance_description, instance_tags,
			instance_ami_launch_index, instance_placement,
			instance_product_codes, group_id, reservation_owner_id,
			reservation_id, instance_private_dns_name, instance_name,
			instance_launch_time, instance_key_name, instance_kernel,
			instance_ramdisk, instance_image_id, instance_num,
			instance_image_name, instance_public_dns_name, instance_id,
			instance_instance_type;

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
		super();
		this.instance_state = instance_state;
		this.instance_description = instance_description;
		this.instance_tags = instance_tags;
		this.instance_ami_launch_index = instance_ami_launch_index;
		this.instance_placement = instance_placement;
		this.instance_product_codes = instance_product_codes;
		this.group_id = group_id;
		this.reservation_owner_id = reservation_owner_id;
		this.reservation_id = reservation_id;
		this.instance_private_dns_name = instance_private_dns_name;
		this.instance_name = instance_name;
		this.instance_launch_time = instance_launch_time;
		this.instance_key_name = instance_key_name;
		this.instance_kernel = instance_kernel;
		this.instance_ramdisk = instance_ramdisk;
		this.instance_image_id = instance_image_id;
		this.instance_num = instance_num;
		this.instance_image_name = instance_image_name;
		this.instance_public_dns_name = instance_public_dns_name;
		this.instance_id = instance_id;
		this.instance_instance_type = instance_instance_type;
	}

	public String getInstance_state() {
		return instance_state;
	}

	public void setInstance_state(String instance_state) {
		this.instance_state = instance_state;
	}

	public String getInstance_description() {
		return instance_description;
	}

	public void setInstance_description(String instance_description) {
		this.instance_description = instance_description;
	}

	public String getInstance_tags() {
		return instance_tags;
	}

	public void setInstance_tags(String instance_tags) {
		this.instance_tags = instance_tags;
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

	public String getInstance_name() {
		return instance_name;
	}

	public void setInstance_name(String instance_name) {
		this.instance_name = instance_name;
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

	public String getInstance_id() {
		return instance_id;
	}

	public void setInstance_id(String instance_id) {
		this.instance_id = instance_id;
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
				+ ", instance_description=" + instance_description
				+ ", instance_tags=" + instance_tags
				+ ", instance_ami_launch_index=" + instance_ami_launch_index
				+ ", instance_placement=" + instance_placement
				+ ", instance_product_codes=" + instance_product_codes
				+ ", group_id=" + group_id + ", reservation_owner_id="
				+ reservation_owner_id + ", reservation_id=" + reservation_id
				+ ", instance_private_dns_name=" + instance_private_dns_name
				+ ", instance_name=" + instance_name
				+ ", instance_launch_time=" + instance_launch_time
				+ ", instance_key_name=" + instance_key_name
				+ ", instance_kernel=" + instance_kernel
				+ ", instance_ramdisk=" + instance_ramdisk
				+ ", instance_image_id=" + instance_image_id
				+ ", instance_num=" + instance_num + ", instance_image_name="
				+ instance_image_name + ", instance_public_dns_name="
				+ instance_public_dns_name + ", instance_id=" + instance_id
				+ ", instance_instance_type=" + instance_instance_type + "]";
	}

}
