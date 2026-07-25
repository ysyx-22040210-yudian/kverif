module npi_crdb_top (
  input  logic clk,
  input  logic data_in,
  output logic data_out
);
  logic state;

  always_ff @(posedge clk) begin
    state <= data_in;
  end

  assign data_out = state;
endmodule
