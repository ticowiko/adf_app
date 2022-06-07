var flows_app = new Vue({
  el: '#flows-app',
  data: {
    parameterizable: ["flow_config_id", "flow_config_tab", "flow_name", "step_name", "flow_operation_id", "batch_id", "batch_status"],
    n_stream_lines: 0,
    error_title: null,
    error_message: null,
    flow_configs: [],
    flow_config_id: null,
    flow_config: null,
    flow_config_tab: null,
    flow_name: null,
    step_name: null,
    step: null,
    step_state: null,
    flow_operation_id: null,
    flow_operation: null,
    flow_operation_stream: "stdout",
    flow_operation_sort_column: null,
    flow_operation_sort_asc: null,
    flow_state: null,
    dag_left_to_right: true,
    batch_id: null,
    batch_status: null,
    batch_downstream: null,
    batch_info: null,
    batch_data: null,
    flow_config_upload_file: null,
    implementer_config_upload_file: null
  },
  mounted:function(){
    this.onload();
    setInterval(function () {
      if (
        this.flow_config_tab === "cmd" &&
        this.flow_config !== null &&
        this.flow_config.flowoperation_set.map(e => e.status_summary).includes("RUNNING")
      ) {
        this.refresh_flow_operations();
        this.sort_flow_operations();
      }
    }.bind(this), 1000);
  },
  methods: {
    onload:function() {
      this.load_from_url();
      this.refresh_flow_configs();
    },
    refresh_flow_configs:function() {
      axios({ method: "GET", url: "/ui/api/flow_configs/" }).then(result => {
        this.flow_configs = result.data;
        this.update_flow_config();
        this.update_flow_operation();
        this.update_batch_downstream();
        this.update_batch_info();
        this.sort_flow_operations();
        this.$nextTick(function() {this.render_flow_dag();});
      }, error => {
        this.handle_error(error);
      });
    },
    delete_flow_config:function(flow_config_id) {
      axios({ method: "DELETE", url: "/ui/api/flow_configs/"+flow_config_id+"/", headers: {'X-CSRFToken' : Cookies.get('csrftoken')}}).then(result =>{
        this.refresh_flow_configs();
      }, error =>{
        this.handle_error(error);
      })
    },
    load_from_url:function() {
      var urlParams = new URLSearchParams(window.location.search);
      for (const param of this.parameterizable) {
        if (urlParams.get(param)) {
          this[param] = urlParams.get(param);
        }
      }
    },
    reset_params:function() {
      for (const param of this.parameterizable) {
        this[param] = null;
      }
    },
    reset_error:function() {
      this.error_title = null;
      this.error_message = null;
    },
    handle_error:function(error) {
      console.error(error);
      this.error_title = error.response.data.title;
      this.error_message = error.response.data.message;
    },
    update_flow_config:function() {
      var old_flow_config_id = this.flow_config_id;
      if (this.flow_config_id === null) {
        this.flow_config = null;
      } else {
        for (const flow_config of this.flow_configs) {
          if(flow_config.id == this.flow_config_id) {
            this.flow_config = flow_config;
            this.update_step();
            this.update_flow_operation();
            break;
          }
        }
      }
      if ((old_flow_config_id !== this.flow_config_id) || (this.flow_state === null)) {
        this.fetch_flow_state(this.flow_config_id);
      }
    },
    update_step:function() {
      if (this.step_name === null) {
        this.step = null;
        return;
      }
      for (const flow of this.flow_config.flow_dag.flows) {
        if (flow.name == this.flow_name) {
          for (const step of flow.steps) {
            if (step.name == this.step_name) {
              this.step = step;
              return;
            }
          }
        }
      }
    },
    flip_dag_left_to_right:function() {
      this.dag_left_to_right = !this.dag_left_to_right;
    },
    render_flow_dag:function() {
      if (this.flow_config === null) {
        return;
      }
      var svg = d3.select("svg");
      svg.selectAll("*").remove();
      if (svg._groups[0][0] === null) {
        console.log("(In app) Skipping flow DAG rendering as SVG element is not in DOM");
        return;
      }
      var left_to_right = (this.flow_config_tab !== null) && this.dag_left_to_right;
      render_flow_dag(this.flow_config.flow_dag.flows, this.flow_state, left_to_right=left_to_right, zoomable=true);
    },
    set_flow_operation_sort_column:function(column) {
      this.flow_operation_sort_column = column;
    },
    flip_flow_operation_sort_order:function() {
      if (this.flow_operation_sort_asc === null) {
        this.flow_operation_sort_asc = "true";
      } else if (this.flow_operation_sort_asc === "false") {
        this.flow_operation_sort_asc = "true";
      } else if (this.flow_operation_sort_asc === "true") {
        this.flow_operation_sort_asc = "false";
      }
    },
    flow_operation_sort_is_asc:function() {
      if (this.flow_operation_sort_asc === null) {
        return false;
      } else if (this.flow_operation_sort_asc === "false") {
        return false;
      } else if (this.flow_operation_sort_asc === "true") {
        return true;
      } else {
        return false;
      }
    },
    sort_flow_operations:function() {
      if (this.flow_operation_sort_column === null) {
        return;
      } else if (this.flow_operation_sort_column === "status_summary") {
        status_order = ["RUNNING", "FAILED", "EXTERNALLY_TERMINATED", "USER_TERMINATED", "DONE"]
        this.flow_config.flowoperation_set.sort(
          (a, b) => (
            (a.status_summary != b.status_summary) ? (status_order.indexOf(a.status_summary) - status_order.indexOf(b.status_summary)) : (b.start_time - a.start_time)
          )
        );
      } else if (this.flow_operation_sort_column === "label") {
        this.flow_config.flowoperation_set.sort(
          (a, b) => (
            (a.label != b.label) ? (+(a.label > b.label) - 0.5) : (b.start_time - a.start_time)
          )
        );
      } else if (this.flow_operation_sort_column === "start_time") {
        this.flow_config.flowoperation_set.sort(
          (a, b) => (b.start_time - a.start_time)
        );
      } else if (this.flow_operation_sort_column === "end_time") {
        this.flow_config.flowoperation_set.sort(
          (a, b) => (b.end_time - a.end_time)
        );
      }
      if (this.flow_operation_sort_is_asc()) {
        this.flow_config.flowoperation_set.reverse();
      }
    },
    update_flow_operation:function() {
      if ( (this.flow_operation_id === null) || (this.flow_config === null) ) {
        this.flow_operation = null;
      } else {
        for (const flow_operation of this.flow_config.flowoperation_set) {
          if (flow_operation.id == this.flow_operation_id) {
            this.flow_operation = flow_operation;
          }
        }
      }
    },
    refresh_flow_operations:function() {
      if (this.flow_config_id === null) {
        return;
      }
      axios({ method: "GET", url: "/ui/api/flow_operations/?flow_config_id="+this.flow_config_id, headers: {'X-CSRFToken' : Cookies.get('csrftoken')}}).then(result =>{
        this.flow_config.flowoperation_set = result.data;
        this.update_flow_operation();
      }, error =>{
        this.handle_error(error);
      })
    },
    delete_flow_operation:function(flow_operation_id) {
      axios({ method: "DELETE", url: "/ui/api/flow_operations/"+flow_operation_id+"/", headers: {'X-CSRFToken' : Cookies.get('csrftoken')}}).then(result =>{
        this.refresh_flow_configs();
      }, error =>{
        this.handle_error(error);
      })
    },
    kill_flow_operation:function(flow_operation_id) {
      axios({ method: "PUT", url: "/ui/api/flow_operations_kill/"+flow_operation_id+"/", headers: {'X-CSRFToken' : Cookies.get('csrftoken')}}).then(result =>{
        this.refresh_flow_configs();
      }, error =>{
        this.handle_error(error);
      })
    },
    fetch_flow_state:function(flow_config_id) {
      if ( flow_config_id === null ) {
        this.flow_state = null;
        return;
      }
      axios({ method: "GET", url: "/ui/api/flow_states/"+flow_config_id+"/", headers: {'X-CSRFToken' : Cookies.get('csrftoken')}}).then(result =>{
        this.flow_state = result.data;
        this.$nextTick(function() {this.render_flow_dag();});
      }, error =>{
        console.log(error);
        this.flow_state = null;
        this.$nextTick(function() {this.render_flow_dag();});
        this.handle_error(error);
      })
    },
    fetch_step_state:function() {
      if ( (this.flow_name === null) || (this.step_name === null) ) {
        this.step_state = null;
        return;
      }
      axios({ method: "GET", url: `/ui/api/flow_states/${this.flow_config_id}/${this.flow_name}/${this.step_name}/`, headers: {'X-CSRFToken' : Cookies.get('csrftoken')}}).then(result =>{
        this.step_state = result.data;
      }, error =>{
        this.handle_error(error);
      })
    },
    set_batch_id:function(batch_id) {
      this.batch_status = null;
      this.batch_id = batch_id;
    },
    set_batch_status:function(batch_status) {
      this.batch_id = null;
      this.batch_status = batch_status;
    },
    update_batch_downstream:function() {
      var url;
      if ( (this.flow_config_id === null) || (this.flow_name === null) || (this.step_name === null)) {
        this.batch_downstream = null;
        return;
      }
      if (this.batch_id !== null) {
        url = `/ui/api/flow_downstreams/${this.flow_config_id}/${this.flow_name}/${this.step_name}/${this.batch_id}/`;
      } else {
        url = `/ui/api/flow_downstreams/${this.flow_config_id}/${this.flow_name}/${this.step_name}/`;
        if (this.batch_status !== null) {
          url += `?status=${this.batch_status}`;
        }
      }
      axios({ method: "GET", url: url, headers: {'X-CSRFToken' : Cookies.get('csrftoken')}}).then(result =>{
        this.batch_downstream = result.data;
      }, error =>{
        this.handle_error(error);
      })
    },
    update_batch_info:function() {
      if ( (this.flow_config_id === null) || (this.flow_name === null) || (this.step_name === null) || (this.batch_id === null) ) {
        this.batch_info = null;
        return;
      }
      axios({ method: "GET", url: `/ui/api/flow_batch_info/${this.flow_config_id}/${this.flow_name}/${this.step_name}/${this.batch_id}/`, headers: {'X-CSRFToken' : Cookies.get('csrftoken')}}).then(result =>{
        this.batch_info = result.data;
      }, error =>{
        this.handle_error(error);
      })
    },
    fetch_batch_data:function() {
      if (this.batch_info === null) {
        return;
      }
      axios({ method: "GET", url: `/ui/api/flow_batch_data/${this.flow_config_id}/${this.flow_name}/${this.step_name}/${this.batch_id}/`, headers: {'X-CSRFToken' : Cookies.get('csrftoken')}}).then(result =>{
        if (result.data.length === 0) {
          this.batch_data = null;
        } else {
          this.batch_data = result.data;
        }
      }, error =>{
        this.handle_error(error);
      })
    },
    get_batch_data_columns:function() {
      if (this.batch_data === null) {
        return [];
      }
      return Object.keys(this.batch_data[0]);
    },
    construct_query_string:function(overrides = {}) {
      param_strings = [];
      params = {};
      for (const param of this.parameterizable) {
        if (param in overrides) {
          params[param] = overrides[param];
        } else {
          params[param] = this[param];
        }
      }
      for (const param of this.parameterizable) {
        if (params[param] !== null) {
          param_strings.push(param + "=" + params[param]);
        }
      }
      query_string = param_strings.join("&");
      if (query_string === "") {
        return location.pathname;
      } else {
        return "?" + param_strings.join("&");
      }
    },
    update_history:function() {
      var urlParams = new URLSearchParams(window.location.search);
      if (this.construct_query_string() != urlParams.toString()) {
        history.pushState(null, "ADF web app", this.construct_query_string());
      }
    },
    set_flow_config_id:function(flow_config_id) {
      this.flow_config_id = flow_config_id;
      this.$nextTick(function() {this.render_flow_dag();});
    },
    set_flow_config_tab:function(flow_config_tab) {
      this.flow_config_tab = flow_config_tab;
    },
    set_step_info:function(flow_name, step_name) {
      this.flow_name = flow_name;
      this.step_name = step_name;
      this.flow_config_tab = "dag";
    },
    set_flow_operation_id:function(flow_operation_id) {
      this.flow_operation_id = flow_operation_id;
    },
    set_flow_operation_stream:function(flow_operation_stream) {
      this.flow_operation_stream = flow_operation_stream;
    },
    send_command:function(flow_config_id, subcommand, sub_args, label) {
      axios({
        method: "POST",
        url: "/ui/api/flow_operations/",
        headers: {'X-CSRFToken' : Cookies.get('csrftoken')},
        data: {"flow_config_id": flow_config_id, "subcommand": subcommand, "sub_args": sub_args, "label": label}
      }).then(result =>{
        this.flow_operation_id = result.data.flow_operation_id;
        this.refresh_flow_configs();
      }, error =>{
        this.handle_error(error);
      })
    },
    download_prebuilt:function() {
      window.open(`/ui/api/generate_prebuilt/${this.flow_config_id}/`)
    },
    reset_batches:function() {
      sub_args = `__fcp__ ${this.flow_name} ${this.step_name}`
      label = `Batch reset ${this.flow_name} / ${this.step_name}`;
      if (this.batch_id !== null) {
        label += ` / ${this.batch_id}`;
        sub_args += ` -b ${this.batch_id}`;
      }
      this.send_command(this.flow_config_id, 'reset-batches', sub_args, label);
      this.flow_config_tab = "cmd";
    },
    set_upload_file:function(attr, event) {
      this[attr] = event.target.files[0];
    },
    upload_file:function(attr, url) {
      if (this[attr] === null) {
        console.log("WARNING upload requested but no file is set !")
        return;
      }
      var form_data = new FormData();
      form_data.append("file", this[attr]);
      axios.put(
        url,
        form_data,
        {"headers": {'X-CSRFToken' : Cookies.get('csrftoken'), 'Content-Type': 'multipart/form-data'}}
      ).then(result =>{
        this.refresh_flow_configs();
      }, error =>{
        this.handle_error(error);
      })
    }
  },
  watch: {
    flows:function() {
      this.update_flow_config();
    },
    flow_config_id:function() {
      this.update_history();
      this.update_flow_config();
      this.fetch_flow_state(this.flow_config_id);
    },
    flow_config_tab:function() {
      this.update_history();
      this.update_flow_config();
    },
    flow_name:function() {
      this.update_history();
      this.fetch_step_state();
      this.update_flow_config();
      this.update_batch_downstream();
      this.batch_data = null;
    },
    step_name:function() {
      this.update_history();
      this.fetch_step_state();
      this.update_flow_config();
      this.update_batch_downstream();
      this.batch_data = null;
    },
    flow_operation_id:function() {
      this.update_history();
      this.update_flow_config();
    },
    dag_left_to_right:function() {
      this.render_flow_dag();
    },
    batch_id:function() {
      this.update_history();
      this.update_flow_config();
      this.update_batch_downstream();
      this.update_batch_info();
      this.batch_data = null;
    },
    batch_status:function() {
      this.update_history();
      this.update_flow_config();
      this.update_batch_downstream();
    },
    flow_operation_stream:function() {
      if (this.flow_operation_stream === null) {
        this.flow_operation_stream = "stdout";
      }
    },
    flow_operation_sort_column:function() {
      this.flow_operation_sort_asc = null;
      this.update_history();
      this.sort_flow_operations();
    },
    flow_operation_sort_asc:function(){
      this.update_history();
      this.sort_flow_operations();
    }
  }
})

set_step_info = function(flow_name, step_name) {
  flows_app.set_step_info(flow_name, step_name);
}

render_dag_node = function(flow, step, step_state) {
  ret = '<div style="cursor: pointer;">'
  ret += `\n<table style="align: left;">
<tr>
    <th scope="row">Flow :</th>
    <td>${flow.name}</td>
</tr>
<tr>
    <th scope="row">Step :</th>
    <td>${step.name}</td>
</tr>
<tr>
    <th scope="row">Version :</th>
    <td>${step.version}</td>
</tr>
<tr>
    <th scope="row">Layer :</th>
    <td>${step.layer}</td>
</tr>
</table>`
  total = 0;
  for (const [status, count] of Object.entries(step_state)){
    total += count;
  }
  for (const [status, count] of Object.entries(step_state)){
    ret += `\n<p class=\"${status}\" style=\"width: ${Math.floor(100*count/total)}%;\">${status}: ${count}</p>`;
  }
  ret += '\n</div>'
  return ret;
}

render_flow_dag = function(flows, flow_state, left_to_right = true, zoomable = false) {
  var svg = d3.select("svg");
  svg.selectAll("*").remove();
  if (svg._groups[0][0] === null) {
    console.log("(In func) Skipping flow DAG rendering as SVG element is not in DOM");
    return;
  }
  var inner = svg.append("g");
  var g = new dagreD3.graphlib.Graph({ directed: true }).setGraph({});
  if (left_to_right) {
    g.graph().rankDir = 'LR';
  }
  var render = new dagreD3.render();
  for (const flow of flows) {
    for (const step of flow.steps) {
      g.setNode(
        step.step_id,
        {
          "labelType": "html",
          "label": render_dag_node(flow, step, ((((flow_state || {})[flow.name] || {})[step.name] || {})[step.version] || {})),
          "rx": 5,
          "ry": 5
        }
      )
      for (const upstream_step_id of step.upstream_step_ids) {
        g.setEdge(upstream_step_id, step.step_id, {label: ""});
      }
    }
  }
  render(inner, g);
  var zoom = d3.zoom().on("zoom", function() {
    inner.attr("transform", d3.event.transform);
  });
  svg.call(zoom);
  var initialScale = 0.75;
  svg.call(zoom.transform, d3.zoomIdentity.translate((svg.attr("width") - g.graph().width * initialScale) / 2, 20).scale(initialScale));
  svg.attr('height', g.graph().height * initialScale + 40);
  if (!zoomable) {
    svg.on('.zoom', null);
  }
  svg.selectAll("g.node").on("click", function(id) {
    var split = id.split('/');
    set_step_info(split[1], split[2]);
  });
}
