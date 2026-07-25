module npi_fixture_alu (
  input  logic [7:0] lhs,
  input  logic [7:0] rhs,
  output logic [7:0] result
);
  always_comb begin
    result = lhs + rhs;
  end
endmodule

module npi_fixture_top;
  logic       clk;
  logic [7:0] lhs;
  logic [7:0] rhs;
  wire  [7:0] result;

  npi_fixture_alu u_alu (
    .lhs(lhs),
    .rhs(rhs),
    .result(result)
  );

  initial begin
    clk = 1'b0;
    lhs = 8'h12;
    rhs = 8'h34;
    #1;
    if (result !== 8'h46) $fatal(1, "fixture arithmetic failed");
    $finish;
  end
endmodule
