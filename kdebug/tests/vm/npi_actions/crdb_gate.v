module npi_crdb_top (
  input  clk,
  input  data_in,
  output data_out
);
  reg state;

  always @(posedge clk) begin
    state <= data_in;
  end

  assign data_out = state;
endmodule
