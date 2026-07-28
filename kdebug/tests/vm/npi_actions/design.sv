module npi_fixture_leaf (
  input  logic in,
  output wire  out
);
  assign out = in;
endmodule

module npi_fixture_alu #(
  parameter int WIDTH = 8,
  parameter logic [WIDTH-1:0] BIAS = '0
) (
  input  logic [WIDTH-1:0] lhs,
  input  logic [WIDTH-1:0] rhs,
  output wire  [WIDTH-1:0] result
);
  localparam int RESULT_WIDTH = WIDTH;
  logic [RESULT_WIDTH-1:0] sum;

  function automatic logic [WIDTH-1:0] add_with_bias(
    input logic [WIDTH-1:0] a,
    input logic [WIDTH-1:0] b
  );
    add_with_bias = a + b + BIAS;
  endfunction

  always_comb begin
    sum = add_with_bias(lhs, rhs);
  end

  assign result = sum;
endmodule

module npi_fixture_top;
  localparam int WIDTH = 12;
  logic       clk;
  logic [WIDTH-1:0] lhs;
  logic [WIDTH-1:0] rhs;
  wire  [WIDTH-1:0] result;
  wire probe;
  wire inverted_probe;

  npi_fixture_alu #(
    .WIDTH(WIDTH),
    .BIAS(12'h001)
  ) u_alu (
    .lhs(lhs),
    .rhs(rhs),
    .result(result)
  );

  generate
    if (WIDTH > 8) begin : g_wide
      npi_fixture_leaf u_leaf (
        .in(lhs[0]),
        .out(probe)
      );
    end
  endgenerate

  not u_not(inverted_probe, probe);

  task automatic check_result(input logic [WIDTH-1:0] expected);
    if (result !== expected) $fatal(1, "fixture arithmetic failed");
  endtask

  initial begin
    clk = 1'b0;
    lhs = 12'h012;
    rhs = 12'h034;
    #1;
    check_result(12'h047);
    $finish;
  end
endmodule
