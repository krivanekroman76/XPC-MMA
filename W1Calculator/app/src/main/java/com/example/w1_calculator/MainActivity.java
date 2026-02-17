package com.example.w1_calculator;

import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.TextView;
import androidx.appcompat.app.AppCompatActivity;
import java.text.DecimalFormat;
import java.util.Stack;

public class MainActivity extends AppCompatActivity {

    private TextView tvDisplay;
    private String currentInput = "";
    private boolean isResultShown = false;
    private DecimalFormat decimalFormat = new DecimalFormat("####.####");

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        tvDisplay = findViewById(R.id.tv_display);

        setNumericOnClickListener();
        setOperatorOnClickListener();

        Button btnClear = findViewById(R.id.btn_clear);
        btnClear.setOnClickListener(v -> {
            if (isResultShown) {
                currentInput = "";
                tvDisplay.setText("0");
                isResultShown = false;
            } else if (!currentInput.isEmpty()) {
                currentInput = currentInput.substring(0, currentInput.length() - 1);
                if (currentInput.isEmpty()) {
                    tvDisplay.setText("0");
                } else {
                    tvDisplay.setText(currentInput);
                }
            }
        });

        btnClear.setOnLongClickListener(v -> {
            currentInput = "";
            tvDisplay.setText("0");
            isResultShown = false;
            return true;
        });

        findViewById(R.id.btn_bracket_open).setOnClickListener(v -> {
            if (isResultShown) {
                currentInput = "(";
                isResultShown = false;
            } else {
                if (currentInput.equals("0")) {
                    currentInput = "(";
                } else {
                    currentInput += "(";
                }
            }
            tvDisplay.setText(currentInput);
        });

        findViewById(R.id.btn_bracket_close).setOnClickListener(v -> {
            if (!isResultShown && !currentInput.isEmpty() && !currentInput.equals("0")) {
                currentInput += ")";
                tvDisplay.setText(currentInput);
            }
        });

        findViewById(R.id.btn_equal).setOnClickListener(v -> {
            if (!currentInput.isEmpty() && !isResultShown) {
                String result = calculate(currentInput);
                if (result.equals("Error")) {
                    tvDisplay.setText(result);
                    currentInput = "";
                } else {
                    tvDisplay.setText("=" + result);
                    currentInput = result;
                    isResultShown = true;
                }
            }
        });

        findViewById(R.id.btn_dot).setOnClickListener(v -> {
            if (isResultShown) {
                currentInput = "0.";
                isResultShown = false;
            } else {
                currentInput += ".";
            }
            tvDisplay.setText(currentInput);
        });

        findViewById(R.id.btn_plus_minus).setOnClickListener(v -> {
            if (currentInput.isEmpty() || currentInput.equals("0")) return;

            if (isResultShown) {
                if (currentInput.startsWith("-")) {
                    currentInput = currentInput.substring(1);
                } else {
                    currentInput = "-" + currentInput;
                }
                tvDisplay.setText("=" + currentInput);
                return;
            }

            int lastOpIndex = -1;
            char[] ops = {'+', '-', '*', '/'};
            for (int i = currentInput.length() - 1; i >= 0; i--) {
                char c = currentInput.charAt(i);
                boolean isOp = false;
                for (char op : ops) {
                    if (c == op) {
                        isOp = true;
                        break;
                    }
                }
                
                if (isOp) {
                    // Ignore unary minus that is already part of a negative number like (-2)
                    if (c == '-' && i > 0 && currentInput.charAt(i - 1) == '(') {
                        continue;
                    }
                    lastOpIndex = i;
                    break;
                }
            }

            if (lastOpIndex == -1) {
                if (currentInput.startsWith("(-") && currentInput.endsWith(")")) {
                    currentInput = currentInput.substring(2, currentInput.length() - 1);
                } else if (currentInput.startsWith("-")) {
                    currentInput = currentInput.substring(1);
                } else {
                    currentInput = "(-" + currentInput + ")";
                }
            } else {
                String prefix = currentInput.substring(0, lastOpIndex + 1);
                String lastPart = currentInput.substring(lastOpIndex + 1);
                
                if (lastPart.startsWith("(-") && lastPart.endsWith(")")) {
                    lastPart = lastPart.substring(2, lastPart.length() - 1);
                } else if (!lastPart.isEmpty()) {
                    lastPart = "(-" + lastPart + ")";
                }
                currentInput = prefix + lastPart;
            }
            tvDisplay.setText(currentInput);
        });
    }

    private String calculate(String expression) {
        try {
            return decimalFormat.format(evaluate(expression));
        } catch (Exception e) {
            return "Error";
        }
    }

    private double evaluate(String expression) {
        char[] tokens = expression.toCharArray();
        Stack<Double> values = new Stack<>();
        Stack<Character> ops = new Stack<>();

        for (int i = 0; i < tokens.length; i++) {
            if (tokens[i] == ' ') continue;

            if ((tokens[i] >= '0' && tokens[i] <= '9') || tokens[i] == '.') {
                StringBuilder sb = new StringBuilder();
                while (i < tokens.length && ((tokens[i] >= '0' && tokens[i] <= '9') || tokens[i] == '.')) {
                    sb.append(tokens[i++]);
                }
                values.push(Double.parseDouble(sb.toString()));
                i--;
            } else if (tokens[i] == '(') {
                ops.push(tokens[i]);
            } else if (tokens[i] == ')') {
                while (!ops.isEmpty() && ops.peek() != '(') {
                    values.push(applyOp(ops.pop(), values.pop(), values.pop()));
                }
                if (!ops.isEmpty()) ops.pop();
            } else if (tokens[i] == '+' || tokens[i] == '-' || tokens[i] == '*' || tokens[i] == '/') {
                // Check if this is a unary minus (negative number)
                if (tokens[i] == '-' && (i == 0 || tokens[i-1] == '(')) {
                    StringBuilder sb = new StringBuilder();
                    sb.append('-');
                    i++;
                    while (i < tokens.length && ((tokens[i] >= '0' && tokens[i] <= '9') || tokens[i] == '.')) {
                        sb.append(tokens[i++]);
                    }
                    if (sb.length() > 1) { // We parsed a number after the minus
                        values.push(Double.parseDouble(sb.toString()));
                        i--;
                    } else { // It's just a minus, push it as an operator if needed (unlikely here)
                         ops.push('-');
                    }
                } else {
                    while (!ops.empty() && hasPrecedence(tokens[i], ops.peek())) {
                        values.push(applyOp(ops.pop(), values.pop(), values.pop()));
                    }
                    ops.push(tokens[i]);
                }
            }
        }

        while (!ops.empty()) {
            values.push(applyOp(ops.pop(), values.pop(), values.pop()));
        }

        return values.pop();
    }

    private boolean hasPrecedence(char op1, char op2) {
        if (op2 == '(' || op2 == ')') return false;
        if ((op1 == '*' || op1 == '/') && (op2 == '+' || op2 == '-')) return false;
        return true;
    }

    private double applyOp(char op, double b, double a) {
        switch (op) {
            case '+': return a + b;
            case '-': return a - b;
            case '*': return a * b;
            case '/':
                if (b == 0) throw new UnsupportedOperationException("Cannot divide by zero");
                return a / b;
        }
        return 0;
    }

    private void setNumericOnClickListener() {
        View.OnClickListener listener = v -> {
            Button b = (Button) v;
            String number = b.getText().toString();

            if (isResultShown) {
                currentInput = number;
                isResultShown = false;
            } else {
                if (currentInput.equals("0")) {
                    currentInput = number;
                } else {
                    currentInput += number;
                }
            }
            tvDisplay.setText(currentInput);
        };

        int[] numericButtons = {
                R.id.btn_0, R.id.btn_1, R.id.btn_2, R.id.btn_3, R.id.btn_4,
                R.id.btn_5, R.id.btn_6, R.id.btn_7, R.id.btn_8, R.id.btn_9
        };

        for (int id : numericButtons) {
            findViewById(id).setOnClickListener(listener);
        }
    }

    private void setOperatorOnClickListener() {
        View.OnClickListener listener = v -> {
            Button b = (Button) v;
            String operator = b.getText().toString();

            if (currentInput.isEmpty()) return;

            isResultShown = false;
            char lastChar = currentInput.charAt(currentInput.length() - 1);
            if (lastChar == '+' || lastChar == '-' || lastChar == '*' || lastChar == '/') {
                currentInput = currentInput.substring(0, currentInput.length() - 1) + operator;
            } else {
                currentInput += operator;
            }
            tvDisplay.setText(currentInput);
        };

        int[] operatorButtons = {
                R.id.btn_add, R.id.btn_sub, R.id.btn_mul, R.id.btn_div
        };

        for (int id : operatorButtons) {
            findViewById(id).setOnClickListener(listener);
        }
    }
}
